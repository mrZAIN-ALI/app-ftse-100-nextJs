# backend/app/routers/backtest.py
from datetime import date
from typing import Optional, List, Dict, Any
import requests
import math

from fastapi import APIRouter, HTTPException, Query

from ..core import supa

router = APIRouter(tags=["backtest"])

def _check_conn():
    if not (supa.SUPABASE_URL and supa.SUPABASE_KEY and supa.REST):
        raise HTTPException(status_code=503, detail="Supabase credentials missing")
    return f"{supa.REST}/{supa.TABLE}", supa.HEADERS

def _safe_float(x):
    try:
        if x is None: return None
        return float(x)
    except Exception:
        return None

@router.get("/backtest")
def backtest(
    start: Optional[date] = None,
    end: Optional[date] = None,
    window: int = Query(7, ge=2, le=60),          # rolling stats window
    cost: float = Query(0.0, ge=0.0, le=0.01),    # per-side cost (e.g., 0.001 = 0.10%)
):
    """
    Backtest using predictions table:
    - Uses LAST_CLOSE (entry) -> ACTUAL_CLOSE (exit) on prediction_for date
    - Executes only when signal is LONG or SHORT
    - P/L in points and return % with 2*cost slippage (entry+exit)
    - Rolling directional accuracy & RMSE over `window`
    """
    base, headers = _check_conn()

    # Pull rows with actuals present, ordered by prediction_for asc
    url = f"{base}?select=*&prediction_for=not.is.null&actual_close=not.is.null&order=prediction_for.asc"
    if start:
        url += f"&prediction_for=gte.{start.isoformat()}"
    if end:
        url += f"&prediction_for=lte.{end.isoformat()}"

    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        rows: List[Dict[str, Any]] = r.json() or []
    except Exception as e:
        msg = getattr(e, "response", None)
        raise HTTPException(status_code=502, detail=f"Supabase error: {getattr(msg, 'text', str(e))}")

    if not rows:
        return {"success": True, "summary": {"count": 0}, "series": {}, "table": []}

    # Compute metrics
    dates, lasts, preds, acts, sides = [], [], [], [], []
    dir_hits, abs_errs, pct_errs = [], [], []

    # Derived arrays
    trade_points, trade_ret = [], []    # per row
    cum_points, cum_ret = [], []

    # Helper: map signal -> side
    def map_side(sig: Optional[str]) -> int:
        if sig == "LONG": return 1
        if sig == "SHORT": return -1
        return 0

    cp_sum = 0.0
    cr_sum = 0.0

    for row in rows:
        pf = row.get("prediction_for")
        dates.append(pf)

        last_close = _safe_float(row.get("last_close"))
        pred_close = _safe_float(row.get("predicted_close"))
        act_close  = _safe_float(row.get("actual_close"))

        lasts.append(last_close)
        preds.append(pred_close)
        acts.append(act_close)

        # direction hit
        hit = None
        if last_close is not None and act_close is not None and pred_close is not None:
            up_down_pred = 1 if pred_close >= last_close else -1
            up_down_real = 1 if act_close >= last_close else -1
            hit = (up_down_pred == up_down_real)
        dir_hits.append(hit)

        # errors
        if pred_close is not None and act_close is not None:
            err = (pred_close - act_close)
            abs_errs.append(abs(err))
            pct_errs.append(abs(err) / act_close if act_close else None)
        else:
            abs_errs.append(None)
            pct_errs.append(None)

        # side & P/L
        side = map_side(row.get("signal"))
        sides.append(side)

        if side == 0 or last_close is None or act_close is None:
            points = 0.0
            ret = 0.0
        else:
            diff = act_close - last_close
            gross_ret = side * (diff / last_close)           # return %
            net_ret = gross_ret - (2.0 * cost)               # entry+exit costs
            # points net, approximate costs in points on both sides:
            net_points = side * diff - (last_close * cost + act_close * cost)
            points = net_points
            ret = net_ret

        trade_points.append(points)
        trade_ret.append(ret)

        cp_sum += points
        cr_sum += ret
        cum_points.append(cp_sum)
        cum_ret.append(cr_sum)

    # Rolling stats
    def rolling(arr, w, f):
        out = []
        for i in range(len(arr)):
            lo = max(0, i - w + 1)
            window_vals = [x for x in arr[lo:i+1] if x is not None]
            out.append(f(window_vals) if window_vals else None)
        return out

    # Rolling directional accuracy (%)
    hits_num = [1 if h is True else (0 if h is False else None) for h in dir_hits]
    def mean(arr): 
        valid = [x for x in arr if x is not None]
        return (sum(valid) / len(valid)) if valid else None
    roll_acc = rolling(hits_num, window, mean)
    roll_acc = [round(x * 100.0, 2) if x is not None else None for x in roll_acc]

    # Rolling RMSE
    sq_errs = [( (preds[i]-acts[i])**2 ) if (preds[i] is not None and acts[i] is not None) else None
               for i in range(len(rows))]
    def rmse(vals):
        v = [x for x in vals if x is not None]
        return math.sqrt(sum(v)/len(v)) if v else None
    roll_rmse = rolling(sq_errs, window, rmse)
    roll_rmse = [round(x, 4) if x is not None else None for x in roll_rmse]

    # Summary metrics
    def safe_mean(vals):
        v = [x for x in vals if x is not None]
        return sum(v)/len(v) if v else None

    mae = safe_mean([abs(preds[i]-acts[i]) if preds[i] is not None and acts[i] is not None else None for i in range(len(rows))])
    rmse_all = rmse([sq_errs[i] for i in range(len(rows))])

    # MAPE
    mape = safe_mean([abs((preds[i]-acts[i])/acts[i]) if (preds[i] is not None and acts[i] not in (None, 0)) else None
                      for i in range(len(rows))])
    # Directional accuracy
    da = safe_mean(hits_num)
    da = da * 100.0 if da is not None else None

    # Naive baseline (predict = last_close)
    naive_abs = [abs(lasts[i]-acts[i]) if (lasts[i] is not None and acts[i] is not None) else None for i in range(len(rows))]
    naive_sq  = [((lasts[i]-acts[i])**2) if (lasts[i] is not None and acts[i] is not None) else None for i in range(len(rows))]
    naive_mae = safe_mean(naive_abs)
    naive_rmse = rmse(naive_sq)

    summary = {
        "count": len(rows),
        "executed_trades": sum(1 for s in sides if s != 0),
        "MAE": round(mae, 4) if mae is not None else None,
        "RMSE": round(rmse_all, 4) if rmse_all is not None else None,
        "MAPE_pct": round(mape*100.0, 2) if mape is not None else None,
        "Directional_Accuracy_pct": round(da, 2) if da is not None else None,
        "Naive_MAE": round(naive_mae, 4) if naive_mae is not None else None,
        "Naive_RMSE": round(naive_rmse, 4) if naive_rmse is not None else None,
        "Per_Side_Cost": cost,
        "Window": window,
    }

    series = {
        "dates": dates,
        "cum_pl_points": [round(x, 4) for x in cum_points],
        "cum_return_pct": [round(x*100.0, 3) for x in cum_ret],
        "rolling_directional_accuracy_pct": roll_acc,
        "rolling_rmse": roll_rmse,
    }

    # Optional: include per-row computed values (short table)
    table = []
    for i in range(len(rows)):
        table.append({
            "prediction_for": dates[i],
            "last_close": lasts[i],
            "predicted_close": preds[i],
            "actual_close": acts[i],
            "signal": rows[i].get("signal"),
            "direction_hit": dir_hits[i],
            "abs_error": abs_errs[i],
            "pct_error": pct_errs[i],
            "trade_points": round(trade_points[i], 4),
            "trade_return_pct": round(trade_ret[i]*100.0, 3),
            "cum_pl_points": round(cum_points[i], 4),
            "cum_return_pct": round(cum_ret[i]*100.0, 3),
        })

    return {"success": True, "summary": summary, "series": series, "table": table}
