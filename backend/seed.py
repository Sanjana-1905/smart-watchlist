"""
Seed script — idempotent and non-destructive.

On first run (no demo user exists): full seed — creates demo user, profile,
16 stocks + ~40 days of history from the committed fixture, and adds the
5-symbol demo watchlist.

On every subsequent run: skips the full seed entirely (never touches existing
price_snapshots, user_view_state, or user_profiles), and only self-heals the
demo watchlist by re-adding any of the 5 target symbols that are missing
(e.g. removed during manual testing).

Safe to run on every container startup.
"""
import json
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

from app.core.database import SessionLocal
from app.models import User, Stock, WatchlistItem, PriceSnapshot, UserProfile
from app.core.security import hash_password

IST = ZoneInfo("Asia/Kolkata")
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "market_history.json"
WATCHLIST_SYMBOLS = ["RELIANCE", "TCS", "HDFCBANK", "BEL", "TATASTEEL"]
DEMO_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEMO_EMAIL = "demo@smartwatchlist.dev"
DEMO_PASSWORD = "demo1234"


def ensure_demo_credentials(db):
    """Idempotently guarantee the demo user has working login credentials."""
    user = db.get(User, DEMO_USER_ID)
    if user and not user.password_hash:
        user.email = DEMO_EMAIL
        user.password_hash = hash_password(DEMO_PASSWORD)
        user.display_name = "Demo User"
        db.commit()
        print(f"  Set demo login credentials: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    else:
        print(f"  Demo login already set: {DEMO_EMAIL}")


def ensure_watchlist_symbols(db):
    """Idempotently guarantee the 5 demo symbols are in DEMO_USER_ID's watchlist."""
    added = 0
    for symbol in WATCHLIST_SYMBOLS:
        stock = db.query(Stock).filter(Stock.symbol == symbol).first()
        if not stock:
            print(f"  WARNING: {symbol} not found in stocks table, skipping")
            continue
        exists = (
            db.query(WatchlistItem)
            .filter(WatchlistItem.user_id == DEMO_USER_ID, WatchlistItem.stock_id == stock.id)
            .first()
        )
        if not exists:
            db.add(WatchlistItem(
                id=uuid.uuid4(), user_id=DEMO_USER_ID, stock_id=stock.id,
                added_at=datetime.now(timezone.utc), version=1,
            ))
            added += 1
    if added:
        db.commit()
        print(f"  Self-healed watchlist: added {added} missing symbol(s)")
    else:
        print("  Watchlist already has all 5 demo symbols — nothing to do")


def main():
    db = SessionLocal()
    try:
        existing_user = db.get(User, DEMO_USER_ID)

        if existing_user:
            print("Demo user already exists — skipping full seed (non-destructive).")
            ensure_demo_credentials(db)
            ensure_watchlist_symbols(db)
            print("Seed check complete.")
            return

        print("No existing demo data found — running full seed...")
        user = User(
            id=DEMO_USER_ID,
            created_at=datetime.now(timezone.utc),
            email=DEMO_EMAIL,
            password_hash=hash_password(DEMO_PASSWORD),
            display_name="Demo User",
        )
        db.add(user)
        db.flush()

        db.add(UserProfile(
            user_id=user.id,
            risk_profile="BALANCED",
            attention_style="BALANCED",
            time_horizon="LONG_TERM",
            version=1,
        ))

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
                db.add(PriceSnapshot(
                    id=uuid.uuid4(),
                    stock_id=stock.id,
                    timestamp=datetime.strptime(row["date"], "%Y-%m-%d").replace(hour=15, minute=30, tzinfo=IST),
                    open=row["open"], high=row["high"], low=row["low"], close=row["close"],
                    volume=row["volume"],
                    source="yfinance_fixture",
                ))

        db.commit()

        print(f"Adding {len(WATCHLIST_SYMBOLS)} stocks to demo watchlist...")
        for symbol in WATCHLIST_SYMBOLS:
            stock = stock_by_symbol.get(symbol)
            if not stock:
                print(f"  WARNING: {symbol} missing from fixture, skipping")
                continue
            db.add(WatchlistItem(
                id=uuid.uuid4(), user_id=user.id, stock_id=stock.id,
                added_at=datetime.now(timezone.utc), version=1,
            ))
        db.commit()

        print("\nFull seed complete.")
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
