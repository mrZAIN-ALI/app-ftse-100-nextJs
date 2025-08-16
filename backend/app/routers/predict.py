# backend/app/routers/predict.py
import os
from datetime import timedelta
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import requests

from ..core.yahoo import fetch_ohlc
from ..core.model import predict_next_close
from ..core import supa  # provides SUPABASE_URL, SUPABASE_KEY, REST, etc.

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "best_lstm_model.h5")
SCALER_PATH = os.path.join(BASE_DIR, "models", "scaler.save")

router = APIRouter()
auth_scheme = HTTPBearer()

class PredictOut(BaseModel):
    id: str | None = None
    generated_at: str | None = None
    last_close: float
    predicted_close: float
    direction: str
    band_lower: float
    band_upper: float
    signal: str
    window_start: str
    window_end: str
    prediction_for: str
    model_version: str = "lstm_h5_v1"
    scaler_version: str = "minmax_v1"
    ticker_used: str | None = None

def _next_trading_day(d):
    nd = d + timedelta(days=1)
    while nd.weekday() >= 5:
        nd += timedelta(days=1)
    return nd

def _get_user_id_from_supabase(token: HTTPAuthorizationCredentials = Depends(auth_scheme)) -> str:
    """Ask Supabase Auth to validate the token and return the user's id."""
    if not supa.SUPABASE_URL or not supa.SUPABASE_KEY:
        raise HTTPException(status_code=500, detail="Server misconfigured: Supabase env not set")

    try:
        resp = requests.get(
            f"{supa.SUPABASE_URL}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token.credentials}",
                "apikey": supa.SUPABASE_KEY,  # backend key is fine here
            },
            timeout=10,
        )
        if resp.status_code != 200:
            # Surface the real reason (expired token, etc.)
            raise HTTPException(status_code=401, detail=f"Auth failed: HTTP {resp.status_code} - {resp.text}")
        data = resp.json() or {}
        user_id = data.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Auth failed: user id missing")
        return user_id
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Auth failed: {e}")

@router.get("/predict", response_model=PredictOut)
def predict(user_id: str = Depends(_get_user_id_from_supabase)):
    # 1) Market data
    try:
        df = fetch_ohlc(120)
        ticker_used = "^FTSE"
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Unable to fetch FTSE data: {e}")

    if df is None or df.empty:
        raise HTTPException(status_code=502, detail="No market data returned.")
    if len(df) < 60:
        raise HTTPException(status_code=400, detail="Not enough data for prediction (need >= 60 rows).")

    # 2) Features
    last60 = df.tail(60)[["Close", "High", "Low", "Open", "Volume"]].values
    last_close = float(df["Close"].iloc[-1])
    window_start_dt = df.index[-60].date()
    window_end_dt = df.index[-1].date()
    prediction_for_dt = _next_trading_day(window_end_dt)

    window_start = window_start_dt.isoformat()
    window_end = window_end_dt.isoformat()
    prediction_for = prediction_for_dt.isoformat()

    # 3) Inference
    try:
        pred_close = float(predict_next_close(last60, model_path=MODEL_PATH, scaler_path=SCALER_PATH))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

    # 4) Signal
    direction = "UP" if pred_close >= last_close else "DOWN"
    band_pct = 1.0
    delta = last_close * (band_pct / 100.0)
    band_lower = float(last_close - delta)
    band_upper = float(last_close + delta)
    conf_ok = (pred_close >= band_upper) if direction == "UP" else (pred_close <= band_lower)
    signal = "LONG" if (direction == "UP" and conf_ok) else ("SHORT" if (direction == "DOWN" and conf_ok) else "NO_TRADE")

    # 5) Persist under this user_id
    rec_id, gen_at = None, None
    if supa.is_connected():
        try:
            record = supa.insert_prediction({
                "user_id": user_id,
                "window_start": window_start,
                "window_end": window_end,
                "prediction_for": prediction_for,
                "last_close": last_close,
                "predicted_close": pred_close,
                "direction_pred": direction,
                "band_lower": band_lower,
                "band_upper": band_upper,
                "signal": signal,
                "model_version": "lstm_h5_v1",
                "scaler_version": "minmax_v1",
                "raw_context": {"ticker_used": ticker_used}
            })
            rec_id = record.get("id")
            gen_at = record.get("generated_at")
        except Exception as e:
            print(f"[WARN] Failed to save prediction to Supabase: {e}")
    else:
        print("[INFO] Skipped Supabase save – DB not connected.")

    # 6) Response
    return PredictOut(
        id=rec_id,
        generated_at=gen_at,
        last_close=last_close,
        predicted_close=pred_close,
        direction=direction,
        band_lower=band_lower,
        band_upper=band_upper,
        signal=signal,
        window_start=window_start,
        window_end=window_end,
        prediction_for=prediction_for,
        ticker_used=ticker_used
    )
