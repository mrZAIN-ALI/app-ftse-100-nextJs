import os
import io
from datetime import datetime, timedelta
from typing import List
import pandas as pd
import yfinance as yf
import requests

# --- FTSE100 focus tickers (most reliable first) ---
TICKERS: List[str] = [

    "^FTSE"     # FTSE 100 Index
]

ALLOW_MOCK = os.environ.get("ALLOW_MOCK_DATA", "false").lower() in ("1", "true", "yes")

# --- Helper: Normalize DataFrame to OHLCV ---
def _as_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize Yahoo/Stooq DataFrame to standard OHLCV format."""
    if df is None or df.empty:
        return pd.DataFrame()

    # If MultiIndex (e.g., ("Open","AAPL")), flatten
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]

    required = ["Open", "High", "Low", "Close"]
    if not all(col in df.columns for col in required):
        return pd.DataFrame()

    if "Volume" not in df.columns:
        df["Volume"] = 0

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date")

    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    df.index = pd.to_datetime(df.index)
    return df

# --- Download from Yahoo Finance ---
def _download_yf(symbol: str, days: int) -> pd.DataFrame:
    try:
        df = yf.download(
            symbol,
            period=f"{days}d",
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=True,
            repair=True
        )
        return _as_ohlcv(df)
    except Exception as e:
        print(f"[WARN] Yahoo download failed for {symbol}: {e}")
        return pd.DataFrame()

# --- Fallback: Stooq ---
def _download_stooq(days: int) -> pd.DataFrame:
    try:
        url = "https://stooq.com/q/d/l/?s=ukx&i=d"
        r = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0"
        })
        r.raise_for_status()

        df = pd.read_csv(io.StringIO(r.text))
        if df.empty:
            return pd.DataFrame()

        df.rename(columns=str.strip, inplace=True)
        df["Date"] = pd.to_datetime(df["Date"])
        df.set_index("Date", inplace=True)

        if "Volume" not in df.columns:
            df["Volume"] = 0

        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        end = df.index.max()
        start = end - timedelta(days=days + 10)
        return df.loc[start:end]
    except Exception as e:
        print(f"[WARN] Stooq fallback failed: {e}")
        return pd.DataFrame()

# --- Mock data (optional dev mode) ---
def _generate_mock(days: int) -> pd.DataFrame:
    import numpy as np
    end = datetime.utcnow().date()
    idx = pd.date_range(end - timedelta(days=days * 2), end, freq="B")
    price = 7600.0
    out = []
    for _ in idx:
        price *= (1.0 + np.random.normal(0, 0.003))
        out.append(price)
    close = pd.Series(out, index=idx)
    df = pd.DataFrame({
        "Open": close.shift(1).fillna(close) * (1 + 0.0005),
        "High": close * (1 + 0.003),
        "Low":  close * (1 - 0.003),
        "Close": close,
        "Volume": 0
    }, index=idx)
    return df.tail(days)

# --- Main Fetch Function ---
def fetch_ohlc(days: int = 180) -> pd.DataFrame:
    """Fetch FTSE100 OHLC data from Yahoo, else fallback to Stooq, else mock (if allowed)."""
    for sym in TICKERS:
        df = _download_yf(sym, days)
        if not df.empty:
            print(f"[INFO] Using Yahoo Finance data for {sym}")
            return df

    df = _download_stooq(days)
    if not df.empty:
        print("[INFO] Using Stooq fallback data")
        return df

    if ALLOW_MOCK:
        print("[INFO] Using synthetic mock market data (ALLOW_MOCK_DATA=true)")
        return _generate_mock(days)

    raise RuntimeError("Unable to fetch FTSE 100 data from any source.")
