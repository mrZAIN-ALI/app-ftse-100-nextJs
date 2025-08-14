import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import pandas as pd

from ..core.yahoo import fetch_ohlc
from ..core.model import predict_next_close
from ..core import supa

# ✅ Correct paths to your models folder
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


@router.get("/predict", response_model=PredictOut)
def predict():
    # 1) Fetch market data
    try:
        df = fetch_ohlc(120)
        ticker_used = "^FTSE"
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Unable to fetch FTSE data: {e}")

    if df is None or df.empty:
        raise HTTPException(status_code=502, detail="No market data returned.")

    if len(df) < 60:
        raise HTTPException(status_code=400, detail="Not enough data for prediction (need >= 60 rows).")

    # 2) Prepare input
    last60 = df.tail(60)[["Close", "High", "Low", "Open", "Volume"]].values
    last_close = float(df["Close"].iloc[-1])
    window_start = df.index[-60].date().isoformat()
    window_end = df.index[-1].date().isoformat()
    prediction_for = window_end

    # 3) Predict
    try:
        pred_close = predict_next_close(last60, model_path=MODEL_PATH, scaler_path=SCALER_PATH)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

    # 4) Calculate direction/signal
    direction = "UP" if pred_close >= last_close else "DOWN"
    band_pct = 1.0
    d = last_close * (band_pct / 100.0)
    band_lower = last_close - d
    band_upper = last_close + d
    conf_ok = pred_close >= band_upper if direction == "UP" else pred_close <= band_lower
    signal = "LONG" if (direction == "UP" and conf_ok) else ("SHORT" if (direction == "DOWN" and conf_ok) else "NO_TRADE")

    # 5) Save to Supabase
    try:
        record = supa.insert_prediction({
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
        print(f"[WARN] Failed to save prediction: {e}")
        rec_id, gen_at = None, None

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
