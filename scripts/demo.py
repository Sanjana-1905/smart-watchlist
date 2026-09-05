"""
Deterministic demo control script.

Usage:
    python scripts/demo.py reset      # clear today's mock drift, start clean
    python scripts/demo.py advance    # inject one fixed, reproducible scenario

Design goal: an evaluator running `reset` then `advance` must see the exact
same meaningful-change moment every time, regardless of how long the poller
has been running or how many times the app has been restarted.
"""
import sys
import os
import uuid
from pathlib import Path
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

if (REPO_ROOT / "app").is_dir():
    sys.path.insert(0, str(REPO_ROOT))
elif (REPO_ROOT / "backend" / "app").is_dir():
    sys.path.insert(0, str(REPO_ROOT / "backend"))
else:
    raise RuntimeError("Could not locate backend app package")

from app.core.database import SessionLocal
from app.models import Stock, PriceSnapshot, UserViewState
from sqlalchemy import select, delete


DEMO_USER_IDS = [
    "00000000-0000-0000-0000-000000000001",  # demo@smartwatchlist.dev
]

# Fixed, reproducible scenario. Percentages are relative to each stock's
# CURRENT latest close at the time `advance` is run (i.e., whatever `reset`
# left as the baseline), not to a hardcoded absolute price.
SCENARIO = {
    "RELIANCE": {"pct_move": 0.062, "volume_multiplier": 3.1, "new_high": True},
    "BEL":      {"pct_move": 0.041, "volume_multiplier": 2.3, "new_high": True},
    "HDFCBANK": {"pct_move": -0.038, "volume_multiplier": 1.9, "new_high": False},
    "TCS":      {"pct_move": 0.004, "volume_multiplier": 1.05, "new_high": False},
    "TATASTEEL":{"pct_move": -0.006, "volume_multiplier": 0.95, "new_high": False},
}


def get_latest_snapshot(db, stock_id):
    return db.scalar(
        select(PriceSnapshot)
        .where(PriceSnapshot.stock_id == stock_id)
        .order_by(PriceSnapshot.timestamp.desc())
    )


def get_avg_recent_volume(db, stock_id, exclude_today=True):
    snaps = db.scalars(
        select(PriceSnapshot)
        .where(PriceSnapshot.stock_id == stock_id)
        .order_by(PriceSnapshot.timestamp.desc())
        .limit(50)
    ).all()
    if exclude_today:
        today = datetime.now(timezone.utc).date()
        snaps = [s for s in snaps if s.timestamp.date() != today]
    if not snaps:
        return 1_000_000.0
    return sum(float(s.volume) for s in snaps) / len(snaps)


def cmd_reset():
    db = SessionLocal()
    try:
        today = datetime.now(timezone.utc).date()
        deleted = db.execute(
            delete(PriceSnapshot).where(
                PriceSnapshot.timestamp >= datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
            )
        )
        db.commit()
        print(f"Deleted {deleted.rowcount} snapshot(s) from today.")

        for uid in DEMO_USER_IDS:
            deleted_views = db.execute(
                delete(UserViewState).where(UserViewState.user_id == uuid.UUID(uid))
            )
        db.commit()
        print(f"Cleared view-state for {len(DEMO_USER_IDS)} demo user(s).")

        print("Reset complete. Baseline is now each stock's last historical close.")
        print("Restart the backend so the mock provider re-seeds from this clean state:")
        print("    docker compose restart backend")
    finally:
        db.close()


def cmd_advance():
    db = SessionLocal()
    try:
        stocks = {s.symbol: s for s in db.scalars(select(Stock)).all()}
        now = datetime.now(timezone.utc)

        applied = []
        for symbol, scenario in SCENARIO.items():
            stock = stocks.get(symbol)
            if not stock:
                print(f"WARNING: {symbol} not found in stocks table, skipping.")
                continue

            latest = get_latest_snapshot(db, stock.id)
            if not latest:
                print(f"WARNING: {symbol} has no prior snapshot, skipping.")
                continue

            base_price = float(latest.close)
            new_price = round(base_price * (1 + scenario["pct_move"]), 2)

            avg_volume = get_avg_recent_volume(db, stock.id)
            new_volume = int(avg_volume * scenario["volume_multiplier"])

            snapshot = PriceSnapshot(
                id=uuid.uuid4(),
                stock_id=stock.id,
                timestamp=now,
                open=base_price,
                high=max(base_price, new_price) * 1.001,
                low=min(base_price, new_price) * 0.999,
                close=new_price,
                volume=new_volume,
                source="mock",
            )
            db.add(snapshot)
            applied.append((symbol, base_price, new_price, scenario["pct_move"] * 100, new_volume))

        db.commit()

        print("Scenario applied:\n")
        print(f"{'SYMBOL':<12}{'FROM':>10}{'TO':>10}{'MOVE':>10}{'VOLUME':>14}")
        for symbol, base, new, pct, vol in applied:
            sign = "+" if pct >= 0 else ""
            print(f"{symbol:<12}{base:>10.2f}{new:>10.2f}{sign}{pct:>8.1f}%{vol:>14,}")

        print("\nRefresh /watchlist/changes (or the dashboard) to see the new ranking.")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("reset", "advance"):
        print("Usage: python scripts/demo.py [reset|advance]")
        sys.exit(1)

    if sys.argv[1] == "reset":
        cmd_reset()
    else:
        cmd_advance()
# HOST-EDIT-MARKER-1788571720
