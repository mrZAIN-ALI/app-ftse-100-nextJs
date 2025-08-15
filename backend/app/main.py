from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import asyncio

from .routers import health, ohlc, predict, history, reconcile
from .core import supa

load_dotenv()  # normal load

app = FastAPI(title="FTSE100 API")

# ===== CORS =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== Include Routers =====
app.include_router(health.router)
app.include_router(ohlc.router)
app.include_router(predict.router)
app.include_router(history.router)
app.include_router(reconcile.router)

# ===== DB Connectivity Check After Startup =====
@app.on_event("startup")
async def startup_event():
    print("[INFO] 🚀 Backend API started successfully and ready to accept requests.")
    asyncio.create_task(_post_start_db_check())

async def _post_start_db_check():
    """Retry DB connection a few times after startup."""
    retries = 5
    delay = 1  # seconds

    for attempt in range(1, retries + 1):
        ok, reason = supa.connection_status()
        if ok:
            print(f"[DB] ✅ Connected to Supabase: {reason}")
            return
        else:
            print(f"[DB] (attempt {attempt}/{retries}) ❌ {reason}. Retrying in {delay}s...")
            await asyncio.sleep(delay)

    print("[DB] ❌ Could not connect to Supabase after retries. Check .env, key type, table name, and RLS.")
