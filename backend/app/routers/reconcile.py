from fastapi import APIRouter
from ..core.yahoo import fetch_ohlc
from ..core import supa

router = APIRouter()

@router.post("/reconcile")
def reconcile():
    # load rows missing actual_close
    rows = [r for r in supa.list_predictions(1000) if r.get("actual_close") is None]
    if not rows:
        return {"updated": 0}

    df = fetch_ohlc(365)  # last year, just in case
    updated = 0
    for r in rows:
        # find actual by date (or next trading day if necessary)
        tgt = r.get("prediction_for")
        if tgt is None: 
            continue
        # Try exact date, else next available
        ix = df.index.get_indexer([tgt], method=None)
        if ix[0] == -1:
            # find first row with date >= tgt
            match = df.loc[df.index.date >= __import__("datetime").date.fromisoformat(tgt)]
            if len(match) == 0:
                continue
            actual = float(match["Close"].iloc[0])
        else:
            actual = float(df["Close"].iloc[ix[0]])

        last_close = float(r.get("last_close") or actual)
        abs_err = abs(actual - float(r.get("predicted_close") or actual))
        pct_err = abs_err / (actual or 1.0)
        dir_true = "UP" if actual >= last_close else "DOWN"
        hit = (dir_true == r.get("direction_pred"))

        supa.update_prediction(r["id"], {
            "actual_close": actual,
            "abs_error": abs_err,
            "pct_error": pct_err,
            "direction_hit": hit
        })
        updated += 1

    return {"updated": updated}
