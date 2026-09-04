"""
Seed script — populates the database with demo data.
Reads historical prices from fixtures/market_history.json (offline, no network).
Run with: python seed.py  (from inside backend/, with venv active and DB reachable)
Safe to re-run: clears existing seed data first (idempotent).
"""
import json
import uuid
from datetime import datetime , timezone
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
from pathlib import Path

from app.core.database import SessionLocal
from app.models import User, Stock, WatchlistItem, PriceSnapshot, UserViewState, UserProfile

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "market_history.json"
WATCHLIST_SYMBOLS = ["RELIANCE", "TCS", "HDFCBANK", "BEL", "TATASTEEL"]
DEMO_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

def main():
    
    db = SessionLocal()

    try:
        print("Clearing existing seed data...")
        db.query(UserViewState).delete()
        db.query(WatchlistItem).delete()
        db.query(PriceSnapshot).delete()
        db.query(UserProfile).delete()
        db.query(Stock).delete()
        db.query(User).delete()
        db.commit()

        print("Creating demo user + profile...")
        user = User(id=DEMO_USER_ID, created_at=datetime.now(timezone.utc))
        db.add(user)
        db.flush()

        profile = UserProfile(
            user_id=user.id,
            risk_profile="BALANCED",
            attention_style="BALANCED",
            time_horizon="LONG_TERM",
            version=1,
        )
        db.add(profile)

        print("Loading fixture...")
        fixture = json.loads(FIXTURE_PATH.read_text())

        print(f"Inserting {len(fixture)} stocks + snapshots...")
        stock_by_symbol = {}
        for symbol, info in fixture.items():
            stock = Stock(
                id=uuid.uuid4(),
                symbol=symbol,
                company_name=info["company_name"],
                exchange=info["exchange"],
                sector=info["sector"],
            )
            db.add(stock)
            db.flush()
            stock_by_symbol[symbol] = stock

            for row in info["history"]:
                snap = PriceSnapshot(
                    id=uuid.uuid4(),
                    stock_id=stock.id,
                    timestamp=datetime.strptime(row["date"], "%Y-%m-%d").replace(hour=15, minute=30, tzinfo=IST),
                    open=row["open"],
                    high=row["high"],
                    low=row["low"],
                    close=row["close"],
                    volume=row["volume"],
                    source="yfinance_fixture",
                )
                db.add(snap)

        print(f"Adding {len(WATCHLIST_SYMBOLS)} stocks to demo watchlist...")
        for symbol in WATCHLIST_SYMBOLS:
            stock = stock_by_symbol[symbol]
            item = WatchlistItem(
                id=uuid.uuid4(),
                user_id=user.id,
                stock_id=stock.id,
                added_at=datetime.now(timezone.utc),
                version=1,
            )
            db.add(item)

        db.commit()

        print("\nSeed complete.")
        print(f"  Demo user id: {user.id}")
        print(f"  Stocks: {len(stock_by_symbol)}")
        print(f"  Watchlist items: {len(WATCHLIST_SYMBOLS)}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
