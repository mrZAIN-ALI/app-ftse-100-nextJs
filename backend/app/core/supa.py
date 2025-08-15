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
    clean_k = k.replace('\ufeff', '')  # remove BOM
    clean_vals[clean_k] = v
    if k != clean_k:
        print(f"[env] cleaned key '{k}' -> '{clean_k}'")

# Ensure env vars are set
for k in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
    if not os.getenv(k) and clean_vals.get(k):
        os.environ[k] = clean_vals[k]
        print(f"[env] set {k} from cleaned .env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")

REST = f"{SUPABASE_URL}/rest/v1" if SUPABASE_URL else None
HEADERS = {
    "apikey": SUPABASE_KEY or "",
    "Authorization": f"Bearer {SUPABASE_KEY}" if SUPABASE_KEY else "",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

TABLE = "predictions"

# ===== Core DB Functions =====
def insert_prediction(row):
    r = requests.post(f"{REST}/{TABLE}", headers=HEADERS, data=json.dumps(row), timeout=30)
    r.raise_for_status()
    return r.json()[0]

def list_predictions(limit=500):
    url = f"{REST}/{TABLE}?select=*&order=generated_at.desc&limit={limit}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

def update_prediction(pred_id, patch):
    url = f"{REST}/{TABLE}?id=eq.{pred_id}"
    r = requests.patch(url, headers=HEADERS, data=json.dumps(patch), timeout=30)
    r.raise_for_status()

# ===== Connection Status =====
def connection_status():
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
# app/core/supa.py

def is_connected() -> bool:
    """
    Check if Supabase connection is available.
    Returns True if URL and key are loaded.
    """
    return bool(SUPABASE_URL and SUPABASE_KEY)
