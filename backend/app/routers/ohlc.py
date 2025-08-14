from fastapi import APIRouter, HTTPException
from ..core.yahoo import fetch_ohlc

router = APIRouter()

@router.get("/ohlc")
def ohlc():
    try:
        df = fetch_ohlc(180)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

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
    