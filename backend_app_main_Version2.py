import asyncio, json, base64, logging, os
from aiohttp import web
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.genai import types as genai_types
import google.generativeai as genai

from config import settings
from services.session_firestore import FirestoreSessionService
from services.memory_store import MemoryStore
from services.feedback import FeedbackStore
from services.budget_guard import BudgetGuard
from services.rag_store import RAGStore
from services.drive_docs_index import fetch_doc_text, split_into_chunks
from agents.intent_agent import build_intent_agent
from agents.perception_agent import build_perception_agent
from agents.memory_agent import build_memory_agent
from agents.planning_agent import build_planning_agent
from agents.reflection_agent import build_reflection_agent
from agents.orchestrator_agent import OrchestratorAgent
from agents.tool_wrappers import call_openweather, geocode_address, reverse_geocode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

APP_NAME = "mobile_adk_app"

session_service = None
memory_store = None
feedback_store = None
budget_guard = None
rag_store = None
runner: Runner = None

if settings.google_api_key:
    genai.configure(api_key=settings.google_api_key)

conversation_agent = LlmAgent(
    name="ConversationAgent",
    model=settings.gemini_model_default,
    instruction=(
        "You are a warm, human-like AI. Use perception_summary, memory_context, rag_snippets, tool_results as available. "
        "If missing info, ask succinct clarifying question. Avoid robotic phrasing."
    ),
    input_schema=None,
    output_key="final_response"
)

intent_agent = build_intent_agent(settings.gemini_model_default)
planning_agent = build_planning_agent(settings.gemini_model_default)
reflection_agent = build_reflection_agent(settings.gemini_model_default)
perception_agent = build_perception_agent(settings.gemini_model_default)
memory_agent = build_memory_agent(settings.gemini_model_default)

orchestrator = OrchestratorAgent(
    intent_agent=intent_agent,
    planning_agent=planning_agent,
    reflection_agent=reflection_agent,
    conversation_agent=conversation_agent,
    perception_agent=perception_agent,
    memory_agent=memory_agent
)

async def init_services():
    global session_service, memory_store, feedback_store, budget_guard, rag_store, runner
    if session_service is None:
        session_service = FirestoreSessionService(settings.project_id, settings.firestore_collection_sessions)
        memory_store = MemoryStore(settings.project_id, settings.firestore_collection_memory)
        feedback_store = FeedbackStore(settings.project_id, settings.firestore_collection_feedback)
        budget_guard = BudgetGuard(settings.project_id, max_daily=settings.max_daily_requests)
        rag_store = RAGStore(settings.project_id)
        runner = Runner(agent=orchestrator, app_name=APP_NAME, session_service=session_service)
        logger.info("Services initialized.")

async def ensure_session(user_id: str, session_id: str):
    sess = await session_service.get_session(APP_NAME, user_id, session_id)
    if not sess:
        sess = await session_service.create_session(APP_NAME, user_id, session_id, state={})
    return sess

async def handle_chat(request: web.Request):
    await init_services()
    data = await request.json()
    user_id = data.get("user_id", "anon")
    session_id = data.get("session_id", "default")
    message = data.get("message", "")
    image_b64 = data.get("image_base64")
    weather_loc = data.get("weather_location")
    lat = data.get("lat")
    lng = data.get("lng")
    doc_query = data.get("doc_query")  # optional explicit doc question

    allowed = await budget_guard.increment_and_check(user_id)
    if not allowed:
        return web.json_response({"error": "Daily usage limit reached."}, status=429)

    session = await ensure_session(user_id, session_id)
    retrieved = await memory_store.retrieve_relevant(user_id, message, k=3) if message else []
    session.state["retrieved_memory"] = retrieved
    session.state["user_query"] = message

    # If doc query present or message suggests docs, do RAG retrieval
    if doc_query:
        rag_snips = await rag_store.retrieve(user_id, doc_query, k=5)
        session.state["rag_snippets"] = rag_snips
    else:
        session.state["rag_snippets"] = []

    if image_b64:
        try:
            image_bytes = base64.b64decode(image_b64)
            img = genai_types.Part.from_bytes(image_bytes, mime_type="image/jpeg")
            mm_prompt = [genai_types.Part(text="Describe salient objects and text for context."), img]
            model = genai.GenerativeModel(settings.gemini_model_default)
            resp = model.generate_content(mm_prompt)
            session.state["image_context"] = resp.text
        except Exception:
            session.state["image_context"] = "Image provided but processing failed."

    tool_results = []
    if weather_loc:
        tool_results.append(await call_openweather(settings.owm_api_key, weather_loc))
    if lat is not None and lng is not None:
        tool_results.append(await reverse_geocode(settings.map_api_key, lat, lng))
    session.state["tool_results"] = tool_results

    await session_service.update_state(APP_NAME, user_id, session_id, session.state)

    response = web.StreamResponse(status=200, reason='OK', headers={'Content-Type': 'application/json'})
    await response.prepare(request)

    final_text = ""
    events = runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=genai_types.Content(role="user", parts=[genai_types.Part(text=message)])
    )

    async for event in events:
        if event.is_content_event() and event.content and event.content.parts:
            chunk = event.content.parts[0].text
            if chunk:
                final_text += chunk
                await response.write(json.dumps({"type":"chunk","data":chunk}).encode()+b"\n")
        if event.is_final_response():
            pass

    updated_session = await session_service.get_session(APP_NAME, user_id, session_id)
    if updated_session:
        updated_session.state["last_response"] = final_text
        await session_service.update_state(APP_NAME, user_id, session_id, updated_session.state)

    await response.write(json.dumps({"type":"final","data":final_text}).encode()+b"\n")
    await response.write_eof()
    return response

async def handle_feedback(request: web.Request):
    await init_services()
    data = await request.json()
    user_id = data.get("user_id","anon")
    session_id = data.get("session_id","default")
    rating = int(data.get("rating",0))
    notes = data.get("notes","")
    await feedback_store.add_feedback(user_id, session_id, "latest", rating, notes)
    return web.json_response({"status":"ok"})

async def handle_add_memory(request: web.Request):
    await init_services()
    data = await request.json()
    user_id = data.get("user_id","anon")
    text = data.get("text","")
    if text:
        await memory_store.add_memory(user_id, text)
    return web.json_response({"status":"ok"})

async def handle_index_doc(request: web.Request):
    """
    Index a Google Doc for RAG:
    {
      "user_id":"u1",
      "doc_id":"<google doc id>"
    }
    """
    await init_services()
    data = await request.json()
    user_id = data.get("user_id","anon")
    doc_id = data.get("doc_id")
    if not doc_id:
        return web.json_response({"error":"doc_id required"}, status=400)
    # Using default creds (service account) inside Cloud Run
    from google.auth import default
    creds, _ = default(scopes=[
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/documents.readonly"
    ])
    text = fetch_doc_text(doc_id, credentials=creds)
    chunks = split_into_chunks(text)
    await rag_store.add_document_chunks(user_id, doc_id, chunks)
    return web.json_response({"status":"indexed","chunks":len(chunks)})

app = web.Application()
app.router.add_post("/chat", handle_chat)
app.router.add_post("/feedback", handle_feedback)
app.router.add_post("/memory", handle_add_memory)
app.router.add_post("/index_doc", handle_index_doc)

if __name__ == "__main__":
    web.run_app(app, port=int(os.getenv("PORT","8080")))