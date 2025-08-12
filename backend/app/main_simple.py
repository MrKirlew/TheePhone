import asyncio
import json
import base64
import logging
import os
from aiohttp import web
import google.generativeai as genai

from config import settings
from services.session_firestore import FirestoreSessionService
from services.memory_store import MemoryStore
from services.feedback import FeedbackStore
from services.budget_guard import BudgetGuard

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

APP_NAME = "mobile_adk_app"

session_service = None
memory_store = None
feedback_store = None
budget_guard = None

if settings.google_api_key:
    genai.configure(api_key=settings.google_api_key)

async def init_services():
    global session_service, memory_store, feedback_store, budget_guard
    
    session_service = FirestoreSessionService(settings.project_id)
    memory_store = MemoryStore(settings.project_id)
    feedback_store = FeedbackStore(settings.project_id)
    budget_guard = BudgetGuard()
    
    logger.info("Services initialized successfully")

async def handle_conversation(request):
    try:
        data = await request.json()
        session_id = data.get("session_id", "default")
        user_message = data.get("message", "")
        
        if not user_message:
            return web.json_response({"error": "No message provided"}, status=400)
        
        # Simple Gemini response
        model = genai.GenerativeModel(settings.gemini_model_default)
        response = model.generate_content(user_message)
        
        return web.json_response({
            "response": response.text,
            "session_id": session_id
        })
        
    except Exception as e:
        logger.error(f"Error in conversation: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def handle_health(request):
    return web.json_response({"status": "healthy", "service": APP_NAME})

async def handle_feedback(request):
    try:
        data = await request.json()
        feedback_type = data.get("type")
        message_id = data.get("message_id")
        
        if feedback_store:
            await feedback_store.record_feedback(message_id, feedback_type)
        
        return web.json_response({"status": "feedback recorded"})
    except Exception as e:
        logger.error(f"Feedback error: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def startup(app):
    await init_services()

async def cleanup(app):
    pass

def create_app():
    app = web.Application()
    
    # Routes
    app.router.add_post("/conversation", handle_conversation)
    app.router.add_get("/health", handle_health)
    app.router.add_post("/feedback", handle_feedback)
    
    # Lifecycle
    app.on_startup.append(startup)
    app.on_cleanup.append(cleanup)
    
    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", "8080"))
    logger.info(f"Starting server on port {port}")
    web.run_app(app, port=port)