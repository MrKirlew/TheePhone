class BudgetGuard:
    def __init__(self, max_daily: int = 500):
        self.max_daily = max_daily
        self.daily_count = {}
    
    async def increment_and_check(self, user_id: str) -> bool:
        if user_id not in self.daily_count:
            self.daily_count[user_id] = 0
        
        if self.daily_count[user_id] >= self.max_daily:
            return False
        
        self.daily_count[user_id] += 1
        return True