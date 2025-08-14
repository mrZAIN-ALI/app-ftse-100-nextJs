from fastapi import APIRouter
from ..core import supa

router = APIRouter()

@router.get("/predictions")
def predictions():
    return {"rows": supa.list_predictions(500)}
