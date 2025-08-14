from fastapi import APIRouter
from ..core.yahoo import fetch_ohlc

router = APIRouter()

@router.get("/ohlc")
def ohlc():
    df = fetch_ohlc(180)
    rows = [
        {
            "date": idx.date().isoformat(),
            "open": float(r.Open),
            "high": float(r.High),
            "low":  float(r.Low),
            "close": float(r.Close),
            "volume": float(r.Volume),
        }
        for idx, r in df.iterrows()
    ]
    return {"rows": rows}
