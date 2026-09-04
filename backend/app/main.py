from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.api import stocks, watchlist, profile
from app.jobs.market_poll import start_scheduler

app = FastAPI(title="Smart Watchlist API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stocks.router)
app.include_router(watchlist.router)
app.include_router(profile.router)

_scheduler = None

@app.on_event("startup")
def on_startup():
    global _scheduler
    _scheduler = start_scheduler()

@app.on_event("shutdown")
def on_shutdown():
    if _scheduler:
        _scheduler.shutdown(wait=False)

@app.get("/health")
def health():
    db_status = "ok"
    redis_status = "ok"
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {e}"
    try:
        r = redis.from_url(settings.redis_url)
        r.ping()
    except Exception as e:
        redis_status = f"error: {e}"
    return {"status": "ok", "database": db_status, "redis": redis_status}
