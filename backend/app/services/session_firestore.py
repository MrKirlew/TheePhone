import json
import asyncio
from typing import Dict, Optional
from google.cloud import firestore

class FirestoreSessionService:
    def __init__(self, project_id: str, collection: str = "sessions"):
        self.client = firestore.AsyncClient(project=project_id)
        self.collection = self.client.collection(collection)

    async def create_session(self, app_name: str, user_id: str, session_id: str, state: Dict):
        doc_ref = self.collection.document(f"{app_name}:{user_id}:{session_id}")
        data = {"app_name": app_name, "user_id": user_id, "session_id": session_id, "state": state}
        await doc_ref.set(data)
        return data

    async def get_session(self, app_name: str, user_id: str, session_id: str):
        doc_ref = self.collection.document(f"{app_name}:{user_id}:{session_id}")
        snap = await doc_ref.get()
        if snap.exists:
            return snap.to_dict()
        return None

    async def update_state(self, app_name: str, user_id: str, session_id: str, state: Dict):
        doc_ref = self.collection.document(f"{app_name}:{user_id}:{session_id}")
        await doc_ref.update({"state": state})