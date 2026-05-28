import os
from dotenv import load_dotenv
from supabase import create_client, Client
import redis

# Load variables from .env
load_dotenv()

# ==========================================
# 1. SUPABASE CONNECTION (For Audit & Evidence)
# ==========================================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase_client():
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            print("[DB] Supabase Connected Successfully!")
            return supabase
        except Exception as e:
            print(f"[DB] Supabase Error: {e}")
            return None
    else:
        print("[DB] Supabase credentials missing in .env. Skipping DB.")
        return None

# ==========================================
# 2. REDIS CONNECTION (For Live Scores)
# ==========================================
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)

def get_redis_client():
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        r.ping() # Connection test
        print("[DB] Redis Connected Successfully!")
        return r
    except Exception as e:
        print(f"[DB] Redis not running (using fallback memory): {e}")
        return None

# Initialize clients
supabase_db = get_supabase_client()
redis_db = get_redis_client()