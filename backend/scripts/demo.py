"""
backend/scripts/demo.py — Deterministic Real-History Replay Demo Controller

Product Principle: SIMULATE THE USER, NOT THE MARKET.
Market data is strictly REAL yfinance data stored in price_snapshots.

Usage:
    docker compose exec backend python scripts/demo.py reset
    docker compose exec backend python scripts/demo.py advance

Timeline (Real History Replay):
    Session A Baseline (e.g. 2026-09-03):
        USER LAST CHECKED HERE (UserViewState.last_viewed_price = Session A price)

    Session B Evaluated (e.g. 2026-09-04):
        REAL yfinance price snapshot evaluated by feature & attention engines.

    TODAY:
        Session B close vs Session A close

    SINCE CHECKED:
        Session B close vs UserViewState.last_viewed_price (Session A close)

    Personalization:
        Same REAL market facts (objective_score is identical).
        Different User Profiles (MOMENTUM vs STABILITY) -> Different personal relevance & final score.
"""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import delete, select
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import (
    PriceSnapshot,
    Stock,
    User,
    UserProfile,
    UserViewState,
    WatchlistItem,
)
from app.repositories import stock_repository, view_state_repository


IST = ZoneInfo("Asia/Kolkata")

PRIMARY_DEMO_USER_ID = "00000000-0000-0000-0000-000000000001"
STABILITY_DEMO_USER_ID = "00000000-0000-0000-0000-000000000002"

DEMO_USER_IDS = [
    PRIMARY_DEMO_USER_ID,
    STABILITY_DEMO_USER_ID,
]

PRIMARY_DEMO_EMAIL = "demo@smartwatchlist.dev"
PRIMARY_DEMO_PASSWORD = "demo1234"
PRIMARY_DEMO_DISPLAY_NAME = "Primary Demo User"

STABILITY_DEMO_EMAIL = "demo.stability@smartwatchlist.dev"
STABILITY_DEMO_PASSWORD = "demo1234"
STABILITY_DEMO_DISPLAY_NAME = "Stability Sam"

# Watchlist symbols for demo users
DEMO_WATCHLIST = [
    "RELIANCE",
    "ASIANPAINT",
    "HDFCBANK",
    "TCS",
    "BEL",
    "TATASTEEL",
    "BAJAJ-AUTO",
    "M&M",
]

# Real historical session dates
BASELINE_SESSION_DATE = "2026-09-03"
EVALUATED_SESSION_DATE = "2026-09-04"


def ensure_demo_users(db):
    """Ensure Primary and Stability demo users & profiles exist."""
    p_uid = uuid.UUID(PRIMARY_DEMO_USER_ID)
    s_uid = uuid.UUID(STABILITY_DEMO_USER_ID)

    # 1. Primary User (Momentum)
    p_user = db.get(User, p_uid)
    if p_user is None:
        p_user = User(
            id=p_uid,
            email=PRIMARY_DEMO_EMAIL,
            password_hash=hash_password(PRIMARY_DEMO_PASSWORD),
            display_name=PRIMARY_DEMO_DISPLAY_NAME,
        )
        db.add(p_user)
    else:
        p_user.email = PRIMARY_DEMO_EMAIL
        p_user.display_name = PRIMARY_DEMO_DISPLAY_NAME
        p_user.password_hash = hash_password(PRIMARY_DEMO_PASSWORD)

    p_prof = db.get(UserProfile, p_uid)
    if p_prof is None:
        p_prof = UserProfile(
            user_id=p_uid,
            risk_profile="AGGRESSIVE",
            attention_style="MOMENTUM",
            time_horizon="SHORT_TERM",
            version=1,
            onboarding_completed=True,
        )
        db.add(p_prof)
    else:
        p_prof.risk_profile = "AGGRESSIVE"
        p_prof.attention_style = "MOMENTUM"
        p_prof.time_horizon = "SHORT_TERM"
        p_prof.onboarding_completed = True

    # 2. Stability User (Stability Sam)
    s_user = db.get(User, s_uid)
    if s_user is None:
        s_user = User(
            id=s_uid,
            email=STABILITY_DEMO_EMAIL,
            password_hash=hash_password(STABILITY_DEMO_PASSWORD),
            display_name=STABILITY_DEMO_DISPLAY_NAME,
        )
        db.add(s_user)
    else:
        s_user.email = STABILITY_DEMO_EMAIL
        s_user.display_name = STABILITY_DEMO_DISPLAY_NAME
        s_user.password_hash = hash_password(STABILITY_DEMO_PASSWORD)

    s_prof = db.get(UserProfile, s_uid)
    if s_prof is None:
        s_prof = UserProfile(
            user_id=s_uid,
            risk_profile="CONSERVATIVE",
            attention_style="STABILITY",
            time_horizon="LONG_TERM",
            version=1,
            onboarding_completed=True,
        )
        db.add(s_prof)
    else:
        s_prof.risk_profile = "CONSERVATIVE"
        s_prof.attention_style = "STABILITY"
        s_prof.time_horizon = "LONG_TERM"
        s_prof.onboarding_completed = True

    db.commit()

    # 3. Synchronize Watchlist
    now = datetime.now(timezone.utc)
    for uid in (p_uid, s_uid):
        existing_items = db.scalars(select(WatchlistItem).where(WatchlistItem.user_id == uid)).all()
        existing_stock_ids = {item.stock_id for item in existing_items}

        for symbol in DEMO_WATCHLIST:
            stock = stock_repository.get_by_symbol(db, symbol)
            if stock and stock.id not in existing_stock_ids:
                db.add(WatchlistItem(id=uuid.uuid4(), user_id=uid, stock_id=stock.id, added_at=now, version=1))
    db.commit()


def get_snapshot_for_date(db, stock_id, target_date_str):
    """Fetch real PriceSnapshot for a given IST date string (YYYY-MM-DD)."""
    snapshots = stock_repository.get_history(db, stock_id)
    for s in snapshots:
        ts_ist = s.timestamp.astimezone(IST)
        if ts_ist.strftime("%Y-%m-%d") == target_date_str:
            return s
    return None


def cmd_reset():
    """Reset user baselines to Baseline Session A (2026-09-03)."""
    db = SessionLocal()
    try:
        print("\n" + "=" * 70)
        print("RESETTING DEMO: REAL-HISTORY REPLAY (BASELINE = 2026-09-03)")
        print("=" * 70)

        # Remove any leftover mock snapshots to ensure 100% real data
        db.execute(delete(PriceSnapshot).where(PriceSnapshot.source == "mock"))
        db.commit()

        ensure_demo_users(db)

        p_uid = uuid.UUID(PRIMARY_DEMO_USER_ID)
        s_uid = uuid.UUID(STABILITY_DEMO_USER_ID)

        print("\nSetting user view-state baselines to Session A (2026-09-03):")
        print(f"{'SYMBOL':<12} {'BASELINE PRICE (09-03)':>22} {'EVALUATED PRICE (09-04)':>24} {'MOVE %':>10}")
        print("-" * 72)

        for symbol in DEMO_WATCHLIST:
            stock = stock_repository.get_by_symbol(db, symbol)
            if not stock:
                continue

            snap_a = get_snapshot_for_date(db, stock.id, BASELINE_SESSION_DATE)
            snap_b = get_snapshot_for_date(db, stock.id, EVALUATED_SESSION_DATE)

            if snap_a is None or snap_b is None:
                # Fallback to latest two real snapshots
                history = stock_repository.get_history(db, stock.id)
                if len(history) >= 2:
                    snap_a, snap_b = history[-2], history[-1]
                elif len(history) == 1:
                    snap_a = snap_b = history[0]

            if snap_a:
                price_a = float(snap_a.close)
                price_b = float(snap_b.close) if snap_b else price_a
                move_pct = ((price_b / price_a) - 1) * 100 if price_a > 0 else 0.0

                for uid in (p_uid, s_uid):
                    view_state_repository.upsert(db, uid, stock.id, price_a, snap_a.timestamp)

                print(f"{symbol:<12} {price_a:>22.2f} {price_b:>24.2f} {move_pct:>9.2f}%")

        print("-" * 72)
        print("Demo reset successfully! Both users are set to Session A baseline.")
        print("Market data: 100% REAL yfinance data stored in Postgres.")
        print("=" * 70 + "\n")
    finally:
        db.close()


def cmd_advance():
    """
    Mark both demo users as caught up to the latest persisted market
    observation for every stock they currently watch.

    Important:
    - Does NOT modify market data.
    - Does NOT fabricate prices.
    - Only updates user_view_state.
    - Uses the latest real persisted observation, so immediately after
      advance, "since checked" should be 0% for all watched stocks.
    """
    db = SessionLocal()

    try:
        print("\n" + "=" * 70)
        print("ADVANCING DEMO: MARKING DEMO USERS CAUGHT UP")
        print("=" * 70)

        ensure_demo_users(db)

        p_uid = uuid.UUID(PRIMARY_DEMO_USER_ID)
        s_uid = uuid.UUID(STABILITY_DEMO_USER_ID)

        demo_user_ids = (p_uid, s_uid)

        # --------------------------------------------------------------
        # Build the UNION of symbols currently watched by either demo user.
        # This avoids stale hardcoded DEMO_WATCHLIST mismatches.
        # --------------------------------------------------------------

        from app.models import WatchlistItem, Stock, PriceSnapshot

        rows = (
            db.query(Stock)
            .join(
                WatchlistItem,
                WatchlistItem.stock_id == Stock.id,
            )
            .filter(
                WatchlistItem.user_id.in_(demo_user_ids)
            )
            .distinct()
            .order_by(Stock.symbol)
            .all()
        )

        print()
        print("Updating demo user view-state baselines to latest real observations:")
        print(
            f"{'SYMBOL':<14}"
            f"{'LATEST PRICE':>16}"
            f"{'OBSERVED AT':>28}"
            f"{'SOURCE':>14}"
        )
        print("-" * 72)

        updated = 0
        skipped = 0

        for stock in rows:
            # Use exactly the latest persisted observation for this stock.
            # This aligns the caught-up baseline with what the application
            # currently treats as the latest market observation.
            latest = (
                db.query(PriceSnapshot)
                .filter(
                    PriceSnapshot.stock_id == stock.id
                )
                .order_by(
                    PriceSnapshot.timestamp.desc()
                )
                .first()
            )

            if latest is None:
                skipped += 1
                print(
                    f"{stock.symbol:<14}"
                    f"{'NO DATA':>16}"
                    f"{'-':>28}"
                    f"{'-':>14}"
                )
                continue

            price = float(latest.close)

            # Only update a user if they actually watch this stock.
            for uid in demo_user_ids:
                watches_stock = (
                    db.query(WatchlistItem)
                    .filter(
                        WatchlistItem.user_id == uid,
                        WatchlistItem.stock_id == stock.id,
                    )
                    .first()
                )

                if watches_stock is None:
                    continue

                view_state_repository.upsert(
                    db,
                    uid,
                    stock.id,
                    price,
                    latest.timestamp,
                )

                updated += 1

            print(
                f"{stock.symbol:<14}"
                f"{price:>16.2f}"
                f"{str(latest.timestamp):>28}"
                f"{str(latest.source):>14}"
            )

        db.commit()

        print("-" * 72)
        print()
        print(
            f"Demo advanced successfully: "
            f"{updated} user/stock baseline(s) updated."
        )

        if skipped:
            print(
                f"{skipped} stock(s) skipped because no market observation exists."
            )

        print(
            "Since-checked returns should now be 0% for every "
            "watched stock with market data."
        )
        print(
            "Market observations were NOT modified."
        )
        print("=" * 70 + "\n")

    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("reset", "advance"):
        print("Usage: python scripts/demo.py [reset|advance]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "reset":
        cmd_reset()
    elif cmd == "advance":
        cmd_advance()
