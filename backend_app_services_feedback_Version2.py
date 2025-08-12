from google.cloud import firestore
from typing import Dict

class FeedbackStore:
    def __init__(self, project_id: str, collection: str):
        self.client = firestore.AsyncClient(project=project_id)
        self.collection = self.client.collection(collection)

    async def add_feedback(self, user_id: str, session_id: str, turn_id: str, rating: int, notes: str):
        await self.collection.add({
            "user_id": user_id,
            "session_id": session_id,
            "turn_id": turn_id,
            "rating": rating,
            "notes": notes
        })