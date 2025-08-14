from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import numpy as np
from ..core.yahoo import fetch_ohlc
from ..core.model import predict_next_close

router = APIRouter()

class PredictOut(BaseModel):
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

@router.get("/predict", response_model=PredictOut)
def predict():
    df = fetch_ohlc(120)
    if len(df) < 60:
        raise HTTPException(status_code=500, detail="Not enough market rows")

    last60 = df.tail(60)[["Close","High","Low","Open","Volume"]].values
    last_close = float(df["Close"].iloc[-1])
    window_start = df.index[-60].date().isoformat()
    window_end = df.index[-1].date().isoformat()
    prediction_for = window_end  # reconcile later if needed

    pred_close = predict_next_close(last60)
    direction = "UP" if pred_close >= last_close else "DOWN"
    band_pct = 1.0
    d = last_close * (band_pct/100)
    band_lower = last_close - d
    band_upper = last_close + d
    conf_ok = pred_close >= band_upper if direction=="UP" else pred_close <= band_lower
    signal = "LONG" if (direction=="UP" and conf_ok) else ("SHORT" if (direction=="DOWN" and conf_ok) else "NO_TRADE")

    return PredictOut(
        last_close=last_close,
        predicted_close=pred_close,
        direction=direction,
        band_lower=band_lower,
        band_upper=band_upper,
        signal=signal,
        window_start=window_start,
        window_end=window_end,
        prediction_for=prediction_for,
    )
