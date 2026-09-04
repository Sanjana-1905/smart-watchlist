import logging
import redis as redis_lib
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.market_service import poll_once

logger = logging.getLogger("market_poll")

def _job():
    db = SessionLocal()
    r = redis_lib.from_url(settings.redis_url)
    try:
        result = poll_once(db, r)
        logger.info(f"market_poll: {result}")
    except Exception:
        logger.exception("market_poll failed")
    finally:
        db.close()

def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    # Remove next_run_time=None — let it schedule immediately
    scheduler.add_job(_job, "interval", seconds=60, id="market_poll", replace_existing=True)
    scheduler.start()
    return scheduler
