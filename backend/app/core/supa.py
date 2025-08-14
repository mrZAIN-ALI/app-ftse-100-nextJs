import os, json, requests
from typing import Any, Dict, List, Optional

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
REST = f"{SUPABASE_URL}/rest/v1"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def insert_prediction(row: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.post(f"{REST}/predictions", headers=HEADERS, data=json.dumps(row), timeout=30)
    r.raise_for_status()
    return r.json()[0]

def list_predictions(limit: int = 500) -> List[Dict[str, Any]]:
    url = f"{REST}/predictions?select=*&order=generated_at.desc&limit={limit}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

def update_prediction(pred_id: str, patch: Dict[str, Any]) -> None:
    url = f"{REST}/predictions?id=eq.{pred_id}"
    r = requests.patch(url, headers=HEADERS, data=json.dumps(patch), timeout=30)
    r.raise_for_status()
