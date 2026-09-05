"""Add catalog metadata without modifying history or user collections. Safe to rerun."""
import json
import sys
import uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.database import SessionLocal
from app.models import Stock
from app.repositories import stock_repository

CATALOG_PATH = Path(__file__).resolve().parents[1] / 'fixtures' / 'explore_catalog.json'

def import_catalog(db, path=CATALOG_PATH):
    rows = json.loads(path.read_text())['stocks']
    symbols = [row['symbol'] for row in rows]
    if len(symbols) != len(set(symbols)):
        raise ValueError('Duplicate catalog symbols')
    added = 0
    for row in rows:
        if row['exchange'] != 'NSE' or row['symbol'] != row['symbol'].upper():
            raise ValueError('Invalid catalog entry')
        if stock_repository.get_by_symbol(db, row['symbol']) is None:
            db.add(Stock(id=uuid.uuid4(), **{key: row[key] for key in ('symbol','company_name','exchange','sector')}))
            added += 1
    db.commit()
    return added

if __name__ == '__main__':
    with SessionLocal() as db:
        print(f'Explore catalog: added {import_catalog(db)} stocks; no history or memberships changed.')
