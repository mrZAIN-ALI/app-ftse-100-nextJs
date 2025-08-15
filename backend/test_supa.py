# import os
# import json
# import requests
# from dotenv import load_dotenv, dotenv_values

# # Load environment variables from .env (load explicitly from backend/.env)
# here = os.path.dirname(__file__)
# env_path = os.path.join(here, ".env")
# loaded = load_dotenv(env_path)  # by default does NOT override existing env vars
# print(f"[env] load_dotenv('{env_path}') -> {loaded}")

# # Show what dotenv actually parsed from the file (raw)
# vals = dotenv_values(env_path)

# # Fix BOM in keys if present
# clean_vals = {}
# for k, v in (vals or {}).items():
#     clean_k = k.replace('\ufeff', '')  # Remove BOM if present
#     clean_vals[clean_k] = v
#     if k != clean_k:
#         print(f"[env] cleaned key '{k}' -> '{clean_k}'")

# # Update process environment
# for k in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
#     if not os.getenv(k) and clean_vals.get(k):
#         os.environ[k] = clean_vals[k]
#         print(f"[env] set {k} from cleaned .env")

# # Debug: show loaded values (mask the secret)
# SUPABASE_URL = os.getenv("SUPABASE_URL")
# SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# print(f"[env] SUPABASE_URL = {repr(SUPABASE_URL)}")
# if SUPABASE_KEY:
#     masked = f"{SUPABASE_KEY[:4]}...{SUPABASE_KEY[-4:]}" if len(SUPABASE_KEY) > 8 else SUPABASE_KEY
#     print(f"[env] SUPABASE_SERVICE_ROLE_KEY = '{masked}' (masked)")
# else:
#     print("[env] SUPABASE_SERVICE_ROLE_KEY is not set")

# if not SUPABASE_URL or not SUPABASE_KEY:
#     raise ValueError("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")

# REST_URL = f"{SUPABASE_URL}/rest/v1"
# HEADERS = {
#     "apikey": SUPABASE_KEY,
#     "Authorization": f"Bearer {SUPABASE_KEY}",
#     "Content-Type": "application/json",
#     "Prefer": "return=representation"
# }

# TABLE = "predictions"  # Change if your table name is different

# def insert_test_row():
#     payload = {
#         "window_start": "2099-01-01",
#         "window_end": "2099-01-02",
#         "prediction_for": "2099-01-02",
#         "last_close": 9999.99,
#         "predicted_close": 10000.01,
#         "direction_pred": "UP",
#         "band_lower": 9900.00,
#         "band_upper": 10100.00,
#         "signal": "NO_TRADE",
#         "model_version": "test_model_v1",
#         "scaler_version": "test_scaler_v1",
#         "raw_context": {"ticker_used": "TEST"}
#     }
#     r = requests.post(f"{REST_URL}/{TABLE}", headers=HEADERS, data=json.dumps(payload))
#     r.raise_for_status()
#     data = r.json()
#     print("✅ Inserted row:", data)
#     return data[0]["id"]

# def read_last_rows(limit=5):
#     r = requests.get(f"{REST_URL}/{TABLE}?select=*&order=generated_at.desc&limit={limit}", headers=HEADERS)
#     r.raise_for_status()
#     data = r.json()
#     print(f"📄 Last {limit} rows:", json.dumps(data, indent=2))

# def delete_row(row_id):
#     r = requests.delete(f"{REST_URL}/{TABLE}?id=eq.{row_id}", headers=HEADERS)
#     r.raise_for_status()
#     print(f"🗑️ Deleted row with id {row_id}")

# if __name__ == "__main__":
#     print("🔍 Testing Supabase connectivity...")
#     test_id = insert_test_row()
#     read_last_rows()
#     delete_row(test_id)
#     print("✅ All operations completed successfully.")
