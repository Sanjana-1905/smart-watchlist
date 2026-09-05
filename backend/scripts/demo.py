"""
Deterministic demo script for judge-facing presentations.

Run inside the backend container:
    docker compose exec backend python scripts/demo.py reset
    docker compose exec backend python scripts/demo.py advance

reset:
    - Removes any previously-injected scenario snapshots (safe to rerun).
    - Establishes a clean "just viewed everything" baseline for the demo
      user across all 5 watchlist stocks, using real fixture data.
    - Restores the demo user's profile to a known default (BALANCED).
    Does NOT touch any other user's data (relevant once auth exists).

advance:
    - Injects one new scripted session snapshot for RELIANCE, BEL, and
      HDFCBANK, computed relative to their real historical baseline so the
      attention engine reacts using its normal, unmodified formula.
    - Idempotent: reruns replace only the snapshot rows this script owns
      (source="demo_scenario"), so repeated calls don't compound prices.
"""
import sys
import uuid
from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.models import Stock, PriceSnapshot, UserViewState, UserProfile

DEMO_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
WATCHLIST_SYMBOLS = ["RELIANCE", "TCS", "HDFCBANK", "BEL", "TATASTEEL"]
SCENARIO_SOURCE = "demo_scenario"

# session_return %, volume multiple vs 20-session average
SCENARIO = {
    "RELIANCE": {"pct": 0.062, "volume_ratio": 2.2},   # -> HIGH
    "BEL":      {"pct": 0.038, "volume_ratio": 3.2},   # -> HIGH, new 20d high
    "HDFCBANK": {"pct": -0.034, "volume_ratio": 1.7},  # -> MEDIUM
}


def _get_stock(db, symbol):
    stock = db.query(Stock).filter(Stock.symbol == symbol).first()
    if not stock:
        raise SystemExit(f"Stock {symbol} not found — did seeding run?")
    return stock


def _real_history(db, stock_id, limit=20):
    """Last N real (non-scenario) snapshots, most recent first. Always computes
    off the true fixture baseline, never off a previously-injected scenario row."""
    return (
        db.query(PriceSnapshot)
        .filter(PriceSnapshot.stock_id == stock_id, PriceSnapshot.source != SCENARIO_SOURCE)
        .order_by(PriceSnapshot.timestamp.desc())
        .limit(limit)
        .all()
    )


def cmd_reset(db):
    print("Resetting demo scenario...")

    deleted = db.query(PriceSnapshot).filter(PriceSnapshot.source == SCENARIO_SOURCE).delete()
    print(f"  Removed {deleted} previous scenario snapshot(s)")

    for symbol in WATCHLIST_SYMBOLS:
        stock = _get_stock(db, symbol)
        history = _real_history(db, stock.id, limit=1)
        if not history:
            print(f"  WARNING: no history for {symbol}, skipping baseline")
            continue
        latest = history[0]

        existing = db.get(UserViewState, {"user_id": DEMO_USER_ID, "stock_id": stock.id})
        if existing:
            existing.last_viewed_at = datetime.now(timezone.utc)
            existing.last_viewed_price = latest.close
        else:
            db.add(UserViewState(
                user_id=DEMO_USER_ID, stock_id=stock.id,
                last_viewed_at=datetime.now(timezone.utc),
                last_viewed_price=latest.close,
            ))
    print(f"  Baseline view state set for {len(WATCHLIST_SYMBOLS)} watchlist stocks")

    profile = db.get(UserProfile, DEMO_USER_ID)
    if profile:
        profile.risk_profile = "BALANCED"
        profile.attention_style = "BALANCED"
        profile.time_horizon = "LONG_TERM"
        profile.version += 1
        print("  Profile reset to BALANCED / BALANCED / LONG_TERM")
    else:
        print("  WARNING: no profile found for demo user")

    db.commit()
    print("Reset complete. Dashboard should now show all LOW / 'nothing unusual'.")


def cmd_advance(db):
    print("Advancing market with scripted scenario...")

    for symbol, scenario in SCENARIO.items():
        stock = _get_stock(db, symbol)

        db.query(PriceSnapshot).filter(
            PriceSnapshot.stock_id == stock.id,
            PriceSnapshot.source == SCENARIO_SOURCE,
        ).delete()

        history = _real_history(db, stock.id, limit=20)
        if not history:
            print(f"  WARNING: no history for {symbol}, skipping")
            continue

        latest = history[0]
        avg_volume_20d = sum(float(h.volume) for h in history) / len(history)

        pct = scenario["pct"]
        new_open = float(latest.close)
        new_close = new_open * (1 + pct)
        new_high = max(new_open, new_close) * 1.001
        new_low = min(new_open, new_close) * 0.999
        new_volume = int(avg_volume_20d * scenario["volume_ratio"])
        new_timestamp = datetime.now(timezone.utc)

        db.add(PriceSnapshot(
            id=uuid.uuid4(),
            stock_id=stock.id,
            timestamp=new_timestamp,
            open=new_open, high=new_high, low=new_low, close=new_close,
            volume=new_volume,
            source=SCENARIO_SOURCE,
        ))

        direction = "+" if pct > 0 else ""
        print(f"  {symbol}: {direction}{pct*100:.1f}% move, {scenario['volume_ratio']}x volume -> injected")

    db.commit()
    print("Advance complete. Refresh the dashboard to see the hero moment.")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("reset", "advance"):
        print("Usage: python scripts/demo.py [reset|advance]")
        sys.exit(1)

    db = SessionLocal()
    try:
        if sys.argv[1] == "reset":
            cmd_reset(db)
        else:
            cmd_advance(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
