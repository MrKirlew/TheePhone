import json, asyncio
from typing import Dict, Optional
from google.cloud import firestore
from google.adk.sessions import Session, SessionService

class FirestoreSessionService(SessionService):
    def __init__(self, project_id: str, collection: str):
        self.client = firestore.AsyncClient(project=project_id)
        self.collection = self.client.collection(collection)

    async def create_session(self, app_name: str, user_id: str, session_id: str, state: Dict) -> Session:
        doc_ref = self.collection.document(f"{app_name}:{user_id}:{session_id}")
        data = {"app_name": app_name, "user_id": user_id, "session_id": session_id, "state": state}
        await doc_ref.set(data)
        return Session(app_name=app_name, user_id=user_id, session_id=session_id, state=state)

    async def get_session(self, app_name: str, user_id: str, session_id: str) -> Optional[Session]:
        doc_ref = self.collection.document(f"{app_name}:{user_id}:{session_id}")
        snap = await doc_ref.get()
        if snap.exists:
            data = snap.to_dict()
            return Session(app_name=data["app_name"], user_id=data["user_id"], session_id=data["session_id"], state=data["state"])
        return None

    async def update_state(self, app_name: str, user_id: str, session_id: str, state: Dict):
        doc_ref = self.collection.document(f"{app_name}:{user_id}:{session_id}")
        await doc_ref.update({"state": state})

    async def list_sessions(self, app_name: str, user_id: str):
        q = self.collection.where("app_name", "==", app_name).where("user_id", "==", user_id)
        async for doc in q.stream():
            d = doc.to_dict()
            yield Session(app_name=d["app_name"], user_id=d["user_id"], session_id=d["session_id"], state=d["state"])