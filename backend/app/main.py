from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()

from .routers import health, ohlc, predict
from .routers import history, reconcile

app = FastAPI(title="FTSE100 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000","http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(ohlc.router)
app.include_router(predict.router)
app.include_router(history.router)
app.include_router(reconcile.router)
