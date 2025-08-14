import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

def fetch_ohlc(days: int = 180) -> pd.DataFrame:
    end = datetime.utcnow().date()
    start = end - timedelta(days=days)
    df = yf.download("^FTSE", start=start.isoformat(), end=end.isoformat())[
        ["Open","High","Low","Close","Volume"]
    ].dropna()
    return df
