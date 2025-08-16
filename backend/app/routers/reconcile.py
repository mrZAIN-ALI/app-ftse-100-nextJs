# backend/app/routers/reconcile.py
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import requests

from fastapi import APIRouter, HTTPException, Query

from ..core import supa
from ..core.yahoo import fetch_ohlc

router = APIRouter(tags=["reconcile"])

def _check_conn():
    if not (supa.SUPABASE_URL and supa.SUPABASE_KEY and supa.REST):
        raise HTTPException(status_code=503, detail="Supabase credentials missing")
    return f"{supa.REST}/{supa.TABLE}", supa.HEADERS

def _safe_float(x) -> Optional[float]:
    try:
        return float(x) if x is not None else None
    except Exception:
        return None

def _next_trading_day(d: date) -> date:
    nd = d + timedelta(days=1)
    while nd.weekday() >= 5:  # Sat/Sun
        nd += timedelta(days=1)
    return nd

@router.post("/repair_prediction_for")
def repair_prediction_for(limit: int = Query(5000, ge=1, le=20000)):
    """
    For rows where prediction_for == window_end, move prediction_for to the next trading day
    and clear actual/error fields so /reconcile can refill them.
    """
    base, headers = _check_conn()

    q = f"{base}?select=id,window_end,prediction_for&order=window_end.asc&limit={limit}"
    try:
        r = requests.get(q, headers=headers, timeout=30)
        r.raise_for_status()
        rows = r.json() or []
    except Exception as e:
        msg = getattr(e, "response", None)
        raise HTTPException(status_code=502, detail=f"Supabase error: {getattr(msg, 'text', str(e))}")

    fixed = 0
    skipped = 0

    for row in rows:
        wid = row.get("id")
        we = row.get("window_end")
        pf = row.get("prediction_for")

        if not wid or not we:
            skipped += 1
            continue

        if pf == we:
            try:
                new_pf = _next_trading_day(date.fromisoformat(we)).isoformat()
                supa.update_prediction(wid, {
                    "prediction_for": new_pf,
                    "actual_close": None,
                    "abs_error": None,
                    "pct_error": None,
                    "direction_hit": None,
                })
                fixed += 1
            except Exception as e:
                print(f"[repair] failed id={wid}: {e}")
                skipped += 1
        else:
            skipped += 1

    return {"success": True, "fixed": fixed, "skipped": skipped}

@router.post("/reconcile")
def reconcile(
    force: bool = Query(False, description="If true, recompute even when actual_close is present"),
    days_back: int = Query(730, ge=7, le=3650, description="How many days of OHLC to fetch"),
    limit: int = Query(5000, ge=1, le=20000),
):
    """
    Populate actual_close as the Close on prediction_for (or next trading day),
    and recompute direction_hit, abs_error, pct_error.
    """
    base, headers = _check_conn()

    # 1) Load target rows
    q = f"{base}?select=*&order=prediction_for.asc&limit={limit}"
    if not force:
        q += "&actual_close=is.null"

    try:
        r = requests.get(q, headers=headers, timeout=30)
        r.raise_for_status()
        rows: List[Dict[str, Any]] = r.json() or []
    except Exception as e:
        msg = getattr(e, "response", None)
        raise HTTPException(status_code=502, detail=f"Supabase error: {getattr(msg, 'text', str(e))}")

    if not rows:
        return {"success": True, "updated": 0, "skipped": 0, "reason": "no rows to reconcile"}

    # 2) Build date->close map
    try:
        df = fetch_ohlc(days_back)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"fetch_ohlc failed: {e}")

    if df is None or df.empty:
        raise HTTPException(status_code=502, detail="fetch_ohlc returned no data")

    df = df.copy()
    df.index = df.index.tz_localize(None) if getattr(df.index, "tz", None) else df.index
    close_map: Dict[str, float] = {}
    for ts, row in df.iterrows():
        try:
            close_map[ts.date().isoformat()] = float(row["Close"])
        except Exception:
            continue

    # 3) Fill actuals/errors
    updated, skipped = 0, 0
    for row in rows:
        pid = row.get("id")
        pf_str = row.get("prediction_for")
        last = _safe_float(row.get("last_close"))
        pred = _safe_float(row.get("predicted_close"))

        if not pid or not pf_str:
            skipped += 1
            continue

        actual: Optional[float] = None
        dt = date.fromisoformat(pf_str)
        for _ in range(4):  # look forward a few days (weekend/holiday)
            key = dt.isoformat()
            if key in close_map:
                actual = close_map[key]
                break
            dt = dt + timedelta(days=1)

        if actual is None:
            skipped += 1
            continue

        patch: Dict[str, Any] = {"actual_close": actual}

        if pred is not None:
            err = pred - actual
            patch["abs_error"] = abs(err)
            patch["pct_error"] = (abs(err) / actual) if actual else None

        if last is not None and pred is not None:
            up_pred = 1 if pred >= last else -1
            up_real = 1 if actual >= last else -1
            patch["direction_hit"] = (up_pred == up_real)

        try:
            supa.update_prediction(pid, patch)
            updated += 1
        except Exception as e:
            print(f"[reconcile] update failed for id={pid}: {e}")
            skipped += 1

    return {"success": True, "updated": updated, "skipped": skipped}
