# backend/app/routers/backtest.py
from datetime import date, timedelta
from functools import lru_cache
from typing import Any, Dict, List, Optional

import os
import numpy as np
import pandas as pd
import yfinance as yf
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from pathlib import Path
import joblib
from tensorflow.keras.models import load_model

router = APIRouter(prefix="/backtest", tags=["backtest"])

# ===== Config =====
DEFAULT_TICKER = "^FTSE"
DEFAULT_LOOKBACK = int(os.getenv("LOOKBACK", "60"))
ENV_MODEL_PATH = os.getenv("MODEL_PATH", "")
ENV_SCALER_PATH = os.getenv("SCALER_PATH", "")
FEATURES = ["Close", "High", "Low", "Open", "Volume"]

# ===== Path resolver =====
def _resolve_file(preferred: str, default_name: str) -> str:
    """
    Find file across sensible locations. Returns absolute path or raises FileNotFoundError.
    """
    here = Path(__file__).resolve()                 # .../app/routers/backtest.py
    app_dir = here.parent.parent                    # .../app
    project_root = app_dir.parent                   # .../backend
    cwd = Path.cwd()
    candidates: List[Path] = []

    if preferred:
        p = Path(preferred)
        candidates += [p, cwd / p, project_root / p, app_dir / p]

    candidates += [
        cwd / default_name,
        project_root / default_name,
        app_dir / default_name,
        app_dir / "models" / default_name,          # <-- your files live here
        here.parent / default_name,
        Path("/mnt/data") / default_name,
    ]

    tried = []
    for c in candidates:
        c = c.resolve()
        tried.append(str(c))
        if c.exists():
            print(f"[model-path] Using: {c}")
            return str(c)

    raise FileNotFoundError(
        f"File '{default_name}' not found. Tried:\n" + "\n".join(tried)
    )

# ===== Cached loaders =====
@lru_cache(maxsize=1)
def _load_scaler():
    path = _resolve_file(ENV_SCALER_PATH, "scaler.save")
    return joblib.load(path)

@lru_cache(maxsize=1)
def _load_model():
    path = _resolve_file(ENV_MODEL_PATH, "best_lstm_model.h5")
    return load_model(path, compile=False)  # inference only

# ===== Helpers =====
def _dl_ohlc(ticker: str, start_dt: date, end_dt: date) -> pd.DataFrame:
    # pad backwards for lookback and a bit forward for safety
    ystart = (start_dt - timedelta(days=220)).strftime("%Y-%m-%d")
    yend = (end_dt + timedelta(days=5)).strftime("%Y-%m-%d")
    df = yf.download(ticker, start=ystart, end=yend, auto_adjust=False, progress=False)
    if df.empty:
        raise HTTPException(400, "No data returned from Yahoo Finance.")
    df = df[FEATURES].dropna().copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.sort_index(inplace=True)
    return df

def _predict_window(model, scaler, window_df: pd.DataFrame) -> float:
    X = scaler.transform(window_df.values)             # (lookback, 5)
    X = X.reshape(1, X.shape[0], X.shape[1])           # (1, lookback, 5)
    scaled_pred = float(model.predict(X, verbose=0).reshape(-1)[0])
    dummy = np.zeros((1, len(FEATURES)))
    dummy[0, 0] = scaled_pred                          # Close is index 0
    inv = scaler.inverse_transform(dummy)
    return float(inv[0, 0])

def _direction(prev_close: float, value: float) -> int:
    s = np.sign(value - prev_close)
    return int(s) if s in (-1, 0, 1) else 0

def _first_valid_target(df: pd.DataFrame, want: date, lookback: int) -> Optional[pd.Timestamp]:
    for t in df.index:
        if t.date() < want:
            continue
        idx = df.index.get_indexer([t])[0]
        if idx >= lookback:
            return t
    return None

def _fmt(ts: pd.Timestamp) -> str:
    return ts.strftime("%Y-%m-%d")

# ===== Schemas =====
class PointResponse(BaseModel):
    success: bool
    target_date: str
    lookback: int
    last_close: float
    predicted_close: float
    actual_close: float
    direction_pred: str
    direction_hit: bool
    abs_error: float
    pct_error: float
    accuracy_pct: float
    trade_points: float
    trade_return_pct: float

class BacktestSeries(BaseModel):
    dates: List[str]
    cum_pl_points: List[Optional[float]]
    cum_return_pct: List[Optional[float]]
    rolling_directional_accuracy_pct: List[Optional[float]]
    rolling_rmse: List[Optional[float]]

class BacktestResponse(BaseModel):
    success: bool
    summary: Dict[str, Any]
    series: BacktestSeries
    table: List[Dict[str, Any]]

# ===== Single day (auto-roll forward; no 404 for holidays/insufficient history) =====
@router.get("/point", response_model=PointResponse)
def backtest_point(
    target: date = Query(..., description="Requested date; rolls to next valid trading day if needed"),
    lookback: int = Query(DEFAULT_LOOKBACK, ge=20, le=120),
):
    try:
        model = _load_model()
        scaler = _load_scaler()
    except FileNotFoundError as e:
        raise HTTPException(500, str(e))

    df = _dl_ohlc(DEFAULT_TICKER, target, target)
    t = _first_valid_target(df, target, lookback)
    if t is None:
        # extend 2 weeks forward to find the next trading day with enough history
        df = _dl_ohlc(DEFAULT_TICKER, target, target + timedelta(days=14))
        t = _first_valid_target(df, target, lookback)
        if t is None:
            raise HTTPException(400, "No valid trading day with enough history near the selected date.")

    idx = df.index.get_indexer([t])[0]
    window_df = df.iloc[idx - lookback: idx]
    prev_close = float(window_df["Close"].iloc[-1])
    actual = float(df.loc[t, "Close"])
    pred = _predict_window(model, scaler, window_df[FEATURES])

    abs_err = abs(pred - actual)
    pct_err = (abs_err / abs(actual) * 100.0) if actual != 0 else 0.0
    acc_pct = 100.0 - pct_err
    dir_pred = "UP" if pred >= prev_close else "DOWN"
    hit = (_direction(prev_close, actual) == _direction(prev_close, pred))

    trade_pts = _direction(prev_close, pred) * (actual - prev_close)
    trade_ret = (trade_pts / prev_close) * 100.0 if prev_close != 0 else 0.0

    return PointResponse(
        success=True,
        target_date=_fmt(t),
        lookback=lookback,
        last_close=round(prev_close, 4),
        predicted_close=round(pred, 4),
        actual_close=round(actual, 4),
        direction_pred=dir_pred,
        direction_hit=bool(hit),
        abs_error=round(abs_err, 4),
        pct_error=round(pct_err, 4),
        accuracy_pct=round(acc_pct, 4),
        trade_points=round(trade_pts, 4),
        trade_return_pct=round(trade_ret, 4),
    )

# ===== Range (adhoc only; single Accuracy% = 100 − MAPE%) =====
@router.get("", response_model=BacktestResponse)
def backtest_range(
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    lookback: int = Query(DEFAULT_LOOKBACK, ge=20, le=120),
    window: int = Query(7, ge=2, le=60),
):
    if end is None:
        end = date.today()
    if start is None:
        start = end - timedelta(days=14)
    if start > end:
        raise HTTPException(400, "start cannot be after end")

    try:
        model = _load_model()
        scaler = _load_scaler()
    except FileNotFoundError as e:
        raise HTTPException(500, str(e))

    raw = _dl_ohlc(DEFAULT_TICKER, start, end)
    end = min(end, raw.index.max().date())

    mask = (raw.index.date >= start) & (raw.index.date <= end)
    tdates = list(raw.index[mask])
    rows: List[Dict[str, Any]] = []
    if not tdates:
        raise HTTPException(400, "No trading days found in selected range.")

    for t in tdates:
        idx = raw.index.get_indexer([t])[0]
        if idx < lookback:
            continue
        win = raw.iloc[idx - lookback: idx]
        prev_close = float(win["Close"].iloc[-1])
        actual = float(raw.loc[t, "Close"])
        try:
            pred = _predict_window(model, scaler, win[FEATURES])
        except Exception:
            continue

        error = pred - actual
        abs_err = abs(error)
        mape = (abs_err / abs(actual) * 100.0) if actual != 0 else 0.0
        acc = 100.0 - mape
        hit = (_direction(prev_close, actual) == _direction(prev_close, pred))

        trade_pts = _direction(prev_close, pred) * (actual - prev_close)
        trade_ret = (trade_pts / prev_close) * 100.0 if prev_close != 0 else 0.0

        rows.append({
            "date": _fmt(t),
            "actual": round(actual, 4),
            "pred": round(pred, 4),
            "prev_close": round(prev_close, 4),
            "error": round(error, 4),
            "abs_error": round(abs_err, 4),
            "mape_pct": round(mape, 4),
            "accuracy_pct": round(acc, 4),
            "direction_pred": "UP" if pred >= prev_close else "DOWN",
            "hit": bool(hit),
            "trade_points": round(trade_pts, 4),
            "trade_return_pct": round(trade_ret, 4),
        })

    if not rows:
        raise HTTPException(400, "Not enough history for selected range.")

    df = pd.DataFrame(rows)

    # cumulative series (simple sum; UI only needs shape)
    df["cum_pl_points"] = df["trade_points"].cumsum()
    df["cum_return_pct"] = df["trade_return_pct"].cumsum()

    # rolling metrics
    r_acc: List[Optional[float]] = []
    r_rmse: List[Optional[float]] = []
    for i in range(len(df)):
        if i + 1 < window:
            r_acc.append(None)
            r_rmse.append(None)
        else:
            sl = df.iloc[i + 1 - window: i + 1]
            r_acc.append(round(100.0 * sl["hit"].mean(), 4))
            r_rmse.append(round(np.sqrt((sl["error"] ** 2).mean()), 4))

    # naive: predict prev_close
    naive_err = df["prev_close"] - df["actual"]
    naive_mae = float(np.abs(naive_err).mean())
    naive_rmse = float(np.sqrt((naive_err ** 2).mean()))

    # single Accuracy% for the range
    mape_mean = float(df["mape_pct"].mean())
    summary = {
        "count": int(len(df)),
        "MAE": round(float(df["abs_error"].mean()), 4),
        "RMSE": round(float(np.sqrt((df["error"] ** 2).mean())), 4),
        "MAPE_pct": round(mape_mean, 4),
        "Avg_Accuracy_pct": round(100.0 - mape_mean, 4),  # <-- single indicator
        "Directional_Accuracy_pct": round(100.0 * float(df["hit"].mean()), 2),
        "Naive_MAE": round(naive_mae, 4),
        "Naive_RMSE": round(naive_rmse, 4),
        "Window": int(window),
    }

    series = BacktestSeries(
        dates=df["date"].tolist(),
        cum_pl_points=df["cum_pl_points"].tolist(),
        cum_return_pct=df["cum_return_pct"].tolist(),
        rolling_directional_accuracy_pct=r_acc,
        rolling_rmse=r_rmse,
    )

    return BacktestResponse(
        success=True,
        summary=summary,
        series=series,
        table=df.to_dict(orient="records"),
    )
# --- add at top with other imports ---
from fastapi.responses import StreamingResponse, JSONResponse
from io import StringIO

# try to use Supabase if configured
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
_supabase = None
try:
    if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
        from supabase import create_client, Client
        _supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        print("[DB] backtest router: Supabase client ready")
except Exception as e:
    print(f"[DB] backtest router: Supabase client not available: {e}")

# --- helper to compute the same range result (reused by export/save) ---
def _compute_range(start: date, end: date, lookback: int, window: int):
    # this calls your existing backtest_range logic but returns (summary, df, series)
    model = _load_model()
    scaler = _load_scaler()

    raw = _dl_ohlc(DEFAULT_TICKER, start, end)
    end = min(end, raw.index.max().date())
    mask = (raw.index.date >= start) & (raw.index.date <= end)
    tdates = list(raw.index[mask])
    rows = []
    for t in tdates:
        idx = raw.index.get_indexer([t])[0]
        if idx < lookback:
            continue
        win = raw.iloc[idx - lookback: idx]
        prev_close = float(win["Close"].iloc[-1])
        actual = float(raw.loc[t, "Close"])
        try:
            pred = _predict_window(model, scaler, win[FEATURES])
        except Exception:
            continue

        error = pred - actual
        abs_err = abs(error)
        mape = (abs_err / abs(actual) * 100.0) if actual != 0 else 0.0
        acc = 100.0 - mape
        hit = (_direction(prev_close, actual) == _direction(prev_close, pred))
        trade_pts = _direction(prev_close, pred) * (actual - prev_close)
        trade_ret = (trade_pts / prev_close) * 100.0 if prev_close != 0 else 0.0

        rows.append({
            "date": t.strftime("%Y-%m-%d"),
            "actual": round(actual, 4),
            "pred": round(float(pred), 4),
            "prev_close": round(prev_close, 4),
            "error": round(error, 4),
            "abs_error": round(abs_err, 4),
            "mape_pct": round(mape, 4),
            "accuracy_pct": round(acc, 4),
            "direction_pred": "UP" if pred >= prev_close else "DOWN",
            "hit": bool(hit),
            "trade_points": round(trade_pts, 4),
            "trade_return_pct": round(trade_ret, 4),
        })

    if not rows:
        raise HTTPException(400, "Not enough history for selected range.")

    df = pd.DataFrame(rows)
    df["cum_pl_points"] = df["trade_points"].cumsum()
    df["cum_return_pct"] = df["trade_return_pct"].cumsum()

    # rolling
    r_acc, r_rmse = [], []
    for i in range(len(df)):
        if i + 1 < window:
            r_acc.append(None); r_rmse.append(None)
        else:
            sl = df.iloc[i + 1 - window: i + 1]
            r_acc.append(round(100.0 * sl["hit"].mean(), 4))
            r_rmse.append(round(np.sqrt((sl["error"] ** 2).mean()), 4))

    # naive
    naive_err = df["prev_close"] - df["actual"]
    naive_mae = float(np.abs(naive_err).mean())
    naive_rmse = float(np.sqrt((naive_err ** 2).mean()))

    mape_mean = float(df["mape_pct"].mean())
    summary = {
        "count": int(len(df)),
        "MAE": round(float(df["abs_error"].mean()), 4),
        "RMSE": round(float(np.sqrt((df["error"] ** 2).mean())), 4),
        "MAPE_pct": round(mape_mean, 4),
        "Avg_Accuracy_pct": round(100.0 - mape_mean, 4),
        "Directional_Accuracy_pct": round(100.0 * float(df["hit"].mean()), 2),
        "Naive_MAE": round(naive_mae, 4),
        "Naive_RMSE": round(naive_rmse, 4),
        "Window": int(window),
    }
    series = {
        "dates": df["date"].tolist(),
        "cum_pl_points": df["cum_pl_points"].tolist(),
        "cum_return_pct": df["cum_return_pct"].tolist(),
        "rolling_directional_accuracy_pct": r_acc,
        "rolling_rmse": r_rmse,
    }
    return summary, df, series

# --- 1) CSV Export ---
@router.get("/export.csv")
def export_range_csv(
    start: date = Query(...),
    end: date = Query(...),
    lookback: int = Query(DEFAULT_LOOKBACK, ge=20, le=120),
    window: int = Query(7, ge=2, le=60),
):
    summary, df, _ = _compute_range(start, end, lookback, window)
    # include summary as first rows (prefixed with '#')
    buf = StringIO()
    for k, v in summary.items():
        buf.write(f"# {k},{v}\n")
    df.to_csv(buf, index=False)
    buf.seek(0)
    filename = f"backtest_{start}_{end}.csv"
    return StreamingResponse(buf, media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})

# --- 2) Save Run to Supabase ---
@router.post("/save")
def save_range_to_supabase(
    start: date = Query(...),
    end: date = Query(...),
    lookback: int = Query(DEFAULT_LOOKBACK, ge=20, le=120),
    window: int = Query(7, ge=2, le=60),
):
    if _supabase is None:
        return JSONResponse(status_code=503, content={"success": False, "error": "Supabase not configured"})

    summary, df, series = _compute_range(start, end, lookback, window)

    # upsert into two tables: backtest_runs, backtest_rows
    run_payload = {
        "start_date": str(start),
        "end_date": str(end),
        "lookback": lookback,
        "window": window,
        **summary,
        "model_path": _resolve_file(ENV_MODEL_PATH, "best_lstm_model.h5"),
        "scaler_path": _resolve_file(ENV_SCALER_PATH, "scaler.save"),
    }
    run_res = _supabase.table("backtest_runs").insert(run_payload).execute()
    run_id = run_res.data[0]["id"]

    rows_payload = [
        {
            "backtest_id": run_id,
            **{k: (None if pd.isna(v) else v) for k, v in rec.items()}
        }
        for rec in df.to_dict(orient="records")
    ]
    # batch insert (Supabase can handle arrays)
    _supabase.table("backtest_rows").insert(rows_payload).execute()

    return {"success": True, "run_id": run_id, "summary": summary, "series": series}
