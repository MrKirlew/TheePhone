from typing import List, Dict
from google.cloud import firestore

class MemoryStore:
    def __init__(self, project_id: str, collection: str = "memories"):
        self.client = firestore.AsyncClient(project=project_id)
        self.collection = self.client.collection(collection)
    
    async def add_memory(self, user_id: str, text: str, weight: float = 1.0):
        doc = {
            "user_id": user_id,
            "text": text,
            "weight": weight,
        }
        await self.collection.add(doc)
    
    async def retrieve_relevant(self, user_id: str, query: str, k: int = 3) -> List[str]:
        results = []
        query = self.collection.where("user_id", "==", user_id).limit(k)
        async for doc_snap in query.stream():
            d = doc_snap.to_dict()
            results.append(d.get("text", ""))
        return results