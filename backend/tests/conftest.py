import pytest
import redis as redis_lib
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.core.config import settings
from app.core.current_user import DEMO_USER_ID
from app.models import Stock, WatchlistItem


@pytest.fixture(scope="session")
def client():
    # Deliberately NOT `with TestClient(app) as c` — that triggers main.py's
    # startup event and starts the APScheduler poller inside the test
    # process, which these tests don't need.
    return TestClient(app)


@pytest.fixture(scope="session")
def redis_client():
    r = redis_lib.from_url(settings.redis_url, decode_responses=True)
    yield r
    r.close()


@pytest.fixture()
def db_session():
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture()
def unwatchlisted_symbol(db_session):
    """
    Picks a seeded stock NOT currently on the demo user's watchlist, so
    add/remove tests don't disturb real demo data. Cleans up afterward.
    """
    watchlisted_ids = {
        row[0] for row in db_session.query(WatchlistItem.stock_id)
        .filter(WatchlistItem.user_id == DEMO_USER_ID).all()
    }
    query = db_session.query(Stock)
    if watchlisted_ids:
        query = query.filter(~Stock.id.in_(watchlisted_ids))
    stock = query.first()
    if stock is None:
        pytest.skip("No un-watchlisted stock available for test isolation")

    yield stock.symbol

    item = (
        db_session.query(WatchlistItem)
        .filter(WatchlistItem.user_id == DEMO_USER_ID, WatchlistItem.stock_id == stock.id)
        .first()
    )
    if item:
        db_session.delete(item)
        db_session.commit()
