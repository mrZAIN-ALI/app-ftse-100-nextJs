# backend/app/core/supa.py
import os
import json
import requests
from dotenv import load_dotenv, dotenv_values

# ===== Load and clean .env =====
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # backend/
ENV_PATH = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_PATH)  # normal load
vals = dotenv_values(ENV_PATH)  # raw parse

# Remove BOM from keys if present
clean_vals = {}
for k, v in (vals or {}).items():
    clean_k = k.replace("\ufeff", "")  # remove BOM
    clean_vals[clean_k] = v
    if k != clean_k:
        print(f"[env] cleaned key '{k}' -> '{clean_k}'")

# Ensure env vars are set for anything the app reads later
for k in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_JWT_SECRET"):
    if not os.getenv(k) and clean_vals.get(k):
        os.environ[k] = clean_vals[k]
        print(f"[env] set {k} from cleaned .env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")  # now exported for predict/history/reconcile

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")

REST = f"{SUPABASE_URL}/rest/v1" if SUPABASE_URL else None
HEADERS = {
    "apikey": SUPABASE_KEY or "",
    "Authorization": f"Bearer {SUPABASE_KEY}" if SUPABASE_KEY else "",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

TABLE = os.getenv("PREDICTIONS_TABLE", "predictions")

# ===== Core DB Functions =====
def insert_prediction(row: dict) -> dict:
    """
    Insert a prediction row (server-side with service_role). Returns inserted row.
    """
    if not REST:
        raise RuntimeError("Supabase REST endpoint not configured")
    r = requests.post(f"{REST}/{TABLE}", headers=HEADERS, data=json.dumps(row), timeout=30)
    r.raise_for_status()
    return r.json()[0]

def list_predictions(limit: int = 500) -> list:
    """
    List predictions (server-side). Use ONLY for admin or internal ops.
    """
    if not REST:
        raise RuntimeError("Supabase REST endpoint not configured")
    url = f"{REST}/{TABLE}?select=*&order=generated_at.desc&limit={limit}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

def update_prediction(pred_id: str, patch: dict, user_id: str | None = None) -> None:
    """
    Update a prediction by id. If user_id is provided, also require it to match,
    which prevents accidental cross-user updates when using service_role.
    """
    if not REST:
        raise RuntimeError("Supabase REST endpoint not configured")
    url = f"{REST}/{TABLE}?id=eq.{pred_id}"
    if user_id:
        url += f"&user_id=eq.{user_id}"
    r = requests.patch(url, headers=HEADERS, data=json.dumps(patch), timeout=30)
    r.raise_for_status()

# ===== Connection Status =====
def connection_status() -> tuple[bool, str]:
    """Check if Supabase is reachable."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False, "Supabase credentials missing"
    try:
        r = requests.get(f"{REST}/{TABLE}?select=id&limit=1", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return True, "Connected"
        return False, f"HTTP {r.status_code} - {r.text}"
    except Exception as e:
        return False, str(e)

def is_connected() -> bool:
    """Returns True if URL and key are loaded."""
    return bool(SUPABASE_URL and SUPABASE_KEY)
