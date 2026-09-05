from sqlalchemy import select, func
from app.models import Stock, PriceSnapshot, WatchlistItem
from scripts.import_explore import import_catalog
from tests.test_scoring_regressions import isolated_db  # noqa: F401

def test_catalog_idempotent_and_does_not_import_market_or_user_data(isolated_db):
    db=isolated_db
    def counts():
        return [db.scalar(select(func.count()).select_from(model)) for model in (Stock,PriceSnapshot,WatchlistItem)]
    before=counts()
    added=import_catalog(db)
    after=counts()
    assert after[0] == before[0]+added
    assert after[1:] == before[1:]
    assert import_catalog(db) == 0
    assert counts() == after
    assert after[0] >= 35
