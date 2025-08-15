# backend/app/routers/predict.py
import os
from datetime import timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core.yahoo import fetch_ohlc
from ..core.model import predict_next_close
from ..core import supa

# Paths to model/scaler
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # backend/app
MODEL_PATH = os.path.join(BASE_DIR, "models", "best_lstm_model.h5")
SCALER_PATH = os.path.join(BASE_DIR, "models", "scaler.save")

router = APIRouter()

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
    """Return next Mon–Fri date (no holiday calendar)."""
    nd = d + timedelta(days=1)
    while nd.weekday() >= 5:  # 5=Sat, 6=Sun
        nd += timedelta(days=1)
    return nd

@router.get("/predict", response_model=PredictOut)
def predict():
    # 1) Fetch FTSE 100 market data
    try:
        df = fetch_ohlc(120)  # expects a DatetimeIndex and columns: Close, High, Low, Open, Volume
        ticker_used = "^FTSE"
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Unable to fetch FTSE data: {e}")

    if df is None or df.empty:
        raise HTTPException(status_code=502, detail="No market data returned.")

    if len(df) < 60:
        raise HTTPException(status_code=400, detail="Not enough data for prediction (need >= 60 rows).")

    # 2) Prepare last 60 rows for model
    last60 = df.tail(60)[["Close", "High", "Low", "Open", "Volume"]].values
    last_close = float(df["Close"].iloc[-1])
    window_start_dt = df.index[-60].date()
    window_end_dt = df.index[-1].date()
    # Target = next trading day (simple Mon–Fri roll)
    prediction_for_dt = _next_trading_day(window_end_dt)

    window_start = window_start_dt.isoformat()
    window_end = window_end_dt.isoformat()
    prediction_for = prediction_for_dt.isoformat()

    # 3) Run prediction
    try:
        pred_close = float(predict_next_close(last60, model_path=MODEL_PATH, scaler_path=SCALER_PATH))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

    # 4) Calculate direction & signal (±1% band around last_close)
    direction = "UP" if pred_close >= last_close else "DOWN"
    band_pct = 1.0  # percent
    delta = last_close * (band_pct / 100.0)
    band_lower = float(last_close - delta)
    band_upper = float(last_close + delta)

    conf_ok = (pred_close >= band_upper) if direction == "UP" else (pred_close <= band_lower)
    signal = "LONG" if (direction == "UP" and conf_ok) else ("SHORT" if (direction == "DOWN" and conf_ok) else "NO_TRADE")

    # 5) Save to Supabase ONLY if connected
    rec_id, gen_at = None, None
    if supa.is_connected():
        try:
            record = supa.insert_prediction({
                "window_start": window_start,              # date
                "window_end": window_end,                  # date
                "prediction_for": prediction_for,          # date
                "last_close": float(last_close),           # numeric
                "predicted_close": float(pred_close),      # numeric
                "direction_pred": direction,               # 'UP'|'DOWN'
                "band_lower": float(band_lower),           # numeric
                "band_upper": float(band_upper),           # numeric
                "signal": signal,                          # 'LONG'|'SHORT'|'NO_TRADE'
                "model_version": "lstm_h5_v1",
                "scaler_version": "minmax_v1",
                "raw_context": {"ticker_used": ticker_used}
                # actual_close, direction_hit, abs_error, pct_error remain NULL until reconcile
            })
            rec_id = record.get("id")
            gen_at = record.get("generated_at")
        except Exception as e:
            print(f"[WARN] Failed to save prediction to Supabase: {e}")
    else:
        print("[INFO] Skipped Supabase save – DB not connected.")

    # 6) Return final prediction object
    return PredictOut(
        id=rec_id,
        generated_at=gen_at,
        last_close=float(last_close),
        predicted_close=float(pred_close),
        direction=direction,
        band_lower=float(band_lower),
        band_upper=float(band_upper),
        signal=signal,
        window_start=window_start,
        window_end=window_end,
        prediction_for=prediction_for,
        ticker_used=ticker_used
    )
