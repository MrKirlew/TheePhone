from typing import List, Dict
from google.cloud import firestore
from .embedding import embed_text

class MemoryStore:
    """
    Stores long-term user facts and vector embeddings in Firestore.
    Simple structure: each document: { user_id, text, embedding, weight, created_at }
    """
    def __init__(self, project_id: str, collection: str):
        self.client = firestore.AsyncClient(project=project_id)
        self.collection = self.client.collection(collection)

    async def add_memory(self, user_id: str, text: str, weight: float = 1.0):
        emb = embed_text(text)
        doc = {
            "user_id": user_id,
            "text": text,
            "embedding": emb,
            "weight": weight,
        }
        await self.collection.add(doc)

    async def retrieve_relevant(self, user_id: str, query: str, k: int = 3) -> List[str]:
        # Naive retrieval: fetch all for user & cosine similarity locally (small scale).
        # For production: store pre-filtered or move to vector DB/Matching Engine.
        emb_q = embed_text(query)
        results = []
        async for doc_snap in self.collection.where("user_id", "==", user_id).stream():
            d = doc_snap.to_dict()
            score = self._cosine(emb_q, d["embedding"])
            results.append((score, d["text"]))
        results.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in results[:k]]

    def _cosine(self, a, b):
        import math
        dot = sum(x*y for x,y in zip(a,b))
        na = math.sqrt(sum(x*x for x in a))
        nb = math.sqrt(sum(x*x for x in b))
        return dot / (na * nb + 1e-9)