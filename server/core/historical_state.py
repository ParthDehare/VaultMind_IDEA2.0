import time
from core.db_connections import redis_db

class HistoricalState:
    """Tracks 7-day moving averages and historical volumes in Redis."""
    
    def __init__(self):
        self.redis = redis_db
        # 7 days in seconds
        self.retention_period = 7 * 24 * 60 * 60
        self.stats = {
            "transactions_scanned": 0,
            "critical_alerts": 0,
            "high_risk_flags": 0,
            "confirmed_fraud": 0,
            "cbsi_sum": 0.0
        }
        self.recent_alerts = []
        self.graph_nodes = set()
        self.graph_edges = []

    def update_user_volume(self, emp_id: str, amount: float):
        if not self.redis:
            return
        
        now = time.time()
        key = f"volume_history:{emp_id}"
        
        # Add transaction amount with timestamp as score
        self.redis.zadd(key, {f"{now}:{amount}": now})
        
        # Remove transactions older than 7 days
        self.redis.zremrangebyscore(key, "-inf", now - self.retention_period)

    def get_7_day_average(self, emp_id: str) -> float:
        """Returns the average transaction amount over the last 7 days."""
        if not self.redis:
            return 0.0
            
        key = f"volume_history:{emp_id}"
        records = self.redis.zrange(key, 0, -1)
        
        if not records:
            return 0.0
            
        total_volume = 0.0
        for record in records:
            # record format is "timestamp:amount"
            try:
                _, amount_str = record.split(":")
                total_volume += float(amount_str)
            except ValueError:
                continue
                
        return total_volume / len(records)

historical_state = HistoricalState()
