from google.cloud import firestore
import datetime

class BudgetGuard:
    def __init__(self, project_id: str, collection: str = "adk_usage_counters", max_daily: int = 500):
        self.client = firestore.AsyncClient(project=project_id)
        self.collection = self.client.collection(collection)
        self.max_daily = max_daily

    async def increment_and_check(self, user_id: str) -> bool:
        today = datetime.date.today().isoformat()
        doc_ref = self.collection.document(f"{user_id}:{today}")
        snap = await doc_ref.get()
        if snap.exists:
            data = snap.to_dict()
            count = data["count"] + 1
            if count > self.max_daily:
                return False
            await doc_ref.update({"count": count})
        else:
            await doc_ref.set({"count": 1})
        return True