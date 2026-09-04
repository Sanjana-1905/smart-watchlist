import logging
from fastapi import FastAPI
import redis
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.api import stocks, watchlist, profile
from app.jobs.market_poll import start_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(title="Smart Watchlist API")

app.include_router(stocks.router)
app.include_router(watchlist.router)
app.include_router(profile.router)

_scheduler = None

@app.on_event("startup")
def on_startup():
    global _scheduler
    logger.info(">>> STARTUP EVENT FIRING <<<")
    try:
        _scheduler = start_scheduler()
        logger.info(f">>> SCHEDULER STARTED: {_scheduler} <<<")
        jobs = _scheduler.get_jobs()
        logger.info(f">>> SCHEDULER JOBS: {jobs} <<<")
    except Exception as e:
        logger.exception(">>> STARTUP FAILED <<<")
        raise

@app.on_event("shutdown")
def on_shutdown():
    logger.info(">>> SHUTDOWN EVENT FIRING <<<")
    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info(">>> SCHEDULER SHUTDOWN <<<")

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
