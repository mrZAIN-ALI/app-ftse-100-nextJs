# backend/app/routers/history.py
from datetime import date
from typing import Optional
import io, csv, requests

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse

from ..core import supa

router = APIRouter(tags=["history"])
auth_scheme = HTTPBearer()

def _check_conn():
    if not supa.SUPABASE_URL or not supa.SUPABASE_KEY or not supa.REST:
        raise HTTPException(status_code=503, detail="Supabase credentials missing")
    return f"{supa.REST}/{supa.TABLE}", supa.HEADERS

def _get_user_id_from_supabase(token: HTTPAuthorizationCredentials = Depends(auth_scheme)) -> str:
    """
    Validate the incoming JWT with Supabase Auth and return the user id.
    This avoids local HS256 decode issues.
    """
    if not supa.SUPABASE_URL or not supa.SUPABASE_KEY:
        raise HTTPException(status_code=500, detail="Server misconfigured: Supabase env not set")
    try:
        resp = requests.get(
            f"{supa.SUPABASE_URL}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token.credentials}",
                "apikey": supa.SUPABASE_KEY,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail=f"Auth failed: HTTP {resp.status_code} - {resp.text}")
        data = resp.json() or {}
        uid = data.get("id")
        if not uid:
            raise HTTPException(status_code=401, detail="Auth failed: user id missing")
        return uid
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Auth failed: {e}")

@router.get("/history")
def list_history(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    start: Optional[date] = None,
    end: Optional[date] = None,
    by: str = "generated_at",          # or "prediction_for"
    desc: bool = True,
    format: str = "json",              # "json" | "csv"
    user_id: str = Depends(_get_user_id_from_supabase),
):
    base, headers = _check_conn()

    # Validate sortable/filterable column
    col = by if by in ("generated_at", "prediction_for") else "generated_at"
    order = f"{col}.{'desc' if desc else 'asc'}"

    # Build PostgREST query, scoped to this user
    url = f"{base}?select=*&user_id=eq.{user_id}&order={order}&limit={limit}&offset={offset}"
    if start:
        url += f"&{col}=gte.{start.isoformat()}"
    if end:
        url += f"&{col}=lte.{end.isoformat()}"

    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        rows = r.json() or []
    except Exception as e:
        txt = getattr(getattr(e, "response", None), "text", str(e))
        raise HTTPException(status_code=502, detail=f"Supabase error: {txt}")

    if format.lower() == "csv":
        buf = io.StringIO()
        if rows:
            writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        else:
            writer = csv.writer(buf); writer.writerow(["no","records"])
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=predictions.csv"},
        )

    return {"success": True, "count": len(rows), "offset": offset, "limit": limit, "data": rows}

@router.get("/history/{prediction_id}")
def get_history_item(prediction_id: str, user_id: str = Depends(_get_user_id_from_supabase)):
    base, headers = _check_conn()
    url = f"{base}?select=*&id=eq.{prediction_id}&user_id=eq.{user_id}"
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json() or []
    except Exception as e:
        txt = getattr(getattr(e, "response", None), "text", str(e))
        raise HTTPException(status_code=502, detail=f"Supabase error: {txt}")

    if not data:
        raise HTTPException(status_code=404, detail="Not found")
    return {"success": True, "data": data[0]}
