"""
Deterministic demo control script.

Usage:
    python scripts/demo.py reset
    python scripts/demo.py advance

Design goal:
An evaluator running `reset` then `advance` must see the exact same
meaningful-change moment every time.

IMPORTANT:
- Market/session semantics use Asia/Kolkata (IST).
- PostgreSQL timestamps are stored in UTC.
- DEMO_MODE should be enabled so the background poller does not overwrite
  the deterministic scenario.
"""

import sys
import uuid
from pathlib import Path
from datetime import datetime, timezone, time
from zoneinfo import ZoneInfo

# ---------------------------------------------------------------------------
# IMPORT PATH
# ---------------------------------------------------------------------------

# backend/scripts/demo.py lives beside backend/app/
#
# Host:
#   <repo>/backend/scripts/demo.py
#   <repo>/backend/app/
#
# Docker:
#   /app/scripts/demo.py
#   /app/app/
#
# Therefore the backend root is always one directory above this file.
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select, delete

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import (
    Stock,
    PriceSnapshot,
    UserViewState,
    WatchlistItem,
    User,
    UserProfile,
)


# ---------------------------------------------------------------------------
# TIMEZONE
# ---------------------------------------------------------------------------

IST = ZoneInfo("Asia/Kolkata")


# ---------------------------------------------------------------------------
# DEMO USERS
# ---------------------------------------------------------------------------

PRIMARY_DEMO_USER_ID = "00000000-0000-0000-0000-000000000001"
STABILITY_DEMO_USER_ID = "00000000-0000-0000-0000-000000000002"

DEMO_USER_IDS = [
    PRIMARY_DEMO_USER_ID,
    STABILITY_DEMO_USER_ID,
]

STABILITY_DEMO_EMAIL = "demo.stability@smartwatchlist.dev"
STABILITY_DEMO_PASSWORD = "demo1234"
STABILITY_DEMO_DISPLAY_NAME = "Stability Sam"


# ---------------------------------------------------------------------------
# DEMO SCENARIO
# ---------------------------------------------------------------------------

# These moves are applied relative to the clean historical baseline that
# remains after `reset`.
#
# The scenario intentionally contains:
#
# RELIANCE  -> very strong positive event
# BEL       -> strong positive event
# HDFCBANK  -> meaningful negative event
# TCS       -> ordinary positive movement
# TATASTEEL -> ordinary negative movement
#
# This allows the two profiles to react differently WITHOUT changing the
# underlying market facts.

SCENARIO = {
    "RELIANCE": {
        "pct_move": 0.062,
        "volume_multiplier": 3.1,
        "new_high": True,
    },
    "BEL": {
        "pct_move": 0.041,
        "volume_multiplier": 2.3,
        "new_high": True,
    },
    "HDFCBANK": {
        "pct_move": -0.038,
        "volume_multiplier": 1.9,
        "new_high": False,
    },
    "TCS": {
        "pct_move": 0.004,
        "volume_multiplier": 1.05,
        "new_high": False,
    },
    "TATASTEEL": {
        "pct_move": -0.006,
        "volume_multiplier": 0.95,
        "new_high": False,
    },
}


# ---------------------------------------------------------------------------
# TIME HELPERS
# ---------------------------------------------------------------------------

def get_today_ist_start_utc():
    """
    Return the UTC timestamp corresponding to midnight today in India.

    Example:

        2026-09-05 00:00 IST
        =
        2026-09-04 18:30 UTC

    Why this exists:

    PostgreSQL stores timestamps in UTC, but Indian market sessions are
    determined using Indian local dates.

    Using UTC midnight here would incorrectly leave snapshots such as
    2026-09-04 23:59 UTC in the database even though that timestamp is
    already 2026-09-05 in India.
    """

    now_ist = datetime.now(IST)

    start_of_today_ist = datetime.combine(
        now_ist.date(),
        time.min,
        tzinfo=IST,
    )

    return start_of_today_ist.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# DEMO PROFILE HELPERS
# ---------------------------------------------------------------------------

def ensure_momentum_demo_profile(db):
    """
    Force the primary demo user's profile to:

        AGGRESSIVE
        MOMENTUM
        SHORT_TERM

    This is done every reset because manual profile/onboarding testing may
    modify the demo account.

    reset() is therefore the single source of truth for the deterministic
    Momentum demo identity.
    """

    uid = uuid.UUID(PRIMARY_DEMO_USER_ID)

    profile = db.get(UserProfile, uid)

    if profile is None:
        profile = UserProfile(
            user_id=uid,
            risk_profile="AGGRESSIVE",
            attention_style="MOMENTUM",
            time_horizon="SHORT_TERM",
            version=1,
            onboarding_completed=True,
        )

        db.add(profile)

        print(
            "  Created primary demo profile: "
            "AGGRESSIVE/MOMENTUM/SHORT_TERM."
        )

    else:
        profile.risk_profile = "AGGRESSIVE"
        profile.attention_style = "MOMENTUM"
        profile.time_horizon = "SHORT_TERM"
        profile.onboarding_completed = True
        profile.version += 1

        print(
            "  Reset primary demo user's profile to "
            "AGGRESSIVE/MOMENTUM/SHORT_TERM."
        )

    db.commit()


def ensure_stability_demo_user(db):
    """
    Create or restore the second demo identity.

    Stability Sam sees the SAME:
        - stocks
        - prices
        - volume
        - market observations

    as the primary demo user.

    Only the preference profile differs.

    This allows us to prove:

        same market facts
            ->
        same objective score
            ->
        different preference fit
            ->
        potentially different final attention
    """

    uid = uuid.UUID(STABILITY_DEMO_USER_ID)
    primary_uid = uuid.UUID(PRIMARY_DEMO_USER_ID)

    # ------------------------------------------------------------------
    # USER
    # ------------------------------------------------------------------

    user = db.get(User, uid)

    if user is None:
        user = User(
            id=uid,
            email=STABILITY_DEMO_EMAIL,
            password_hash=hash_password(STABILITY_DEMO_PASSWORD),
            display_name=STABILITY_DEMO_DISPLAY_NAME,
        )

        db.add(user)
        db.commit()

        print(f"  Created user {STABILITY_DEMO_EMAIL}.")

    else:
        print(f"  User {STABILITY_DEMO_EMAIL} already exists.")

    # ------------------------------------------------------------------
    # PROFILE
    # ------------------------------------------------------------------

    profile = db.get(UserProfile, uid)

    if profile is None:
        profile = UserProfile(
            user_id=uid,
            risk_profile="CONSERVATIVE",
            attention_style="STABILITY",
            time_horizon="LONG_TERM",
            version=1,
            onboarding_completed=True,
        )

        db.add(profile)

        print(
            f"  Created profile for {STABILITY_DEMO_EMAIL}: "
            "CONSERVATIVE/STABILITY/LONG_TERM."
        )

    else:
        profile.risk_profile = "CONSERVATIVE"
        profile.attention_style = "STABILITY"
        profile.time_horizon = "LONG_TERM"
        profile.onboarding_completed = True
        profile.version += 1

        print(
            f"  Reset profile for {STABILITY_DEMO_EMAIL} to "
            "CONSERVATIVE/STABILITY/LONG_TERM."
        )

    db.commit()

    # ------------------------------------------------------------------
    # COPY PRIMARY WATCHLIST
    # ------------------------------------------------------------------

    primary_rows = db.execute(
        select(WatchlistItem).where(
            WatchlistItem.user_id == primary_uid
        )
    ).scalars().all()

    primary_stock_ids = {
        item.stock_id
        for item in primary_rows
    }

    existing_rows = db.execute(
        select(WatchlistItem).where(
            WatchlistItem.user_id == uid
        )
    ).scalars().all()

    existing_stock_ids = {
        item.stock_id
        for item in existing_rows
    }

    now = datetime.now(timezone.utc)

    added = 0

    for stock_id in primary_stock_ids - existing_stock_ids:
        db.add(
            WatchlistItem(
                id=uuid.uuid4(),
                user_id=uid,
                stock_id=stock_id,
                added_at=now,
                version=1,
            )
        )

        added += 1

    db.commit()

    print(
        f"  Watchlist synced: {added} stock(s) added "
        f"to match primary demo user "
        f"(total {len(primary_stock_ids)})."
    )


# ---------------------------------------------------------------------------
# MARKET DATA HELPERS
# ---------------------------------------------------------------------------

def get_latest_snapshot(db, stock_id):
    """
    Return the newest stored market observation for a stock.
    """

    return db.scalar(
        select(PriceSnapshot)
        .where(
            PriceSnapshot.stock_id == stock_id
        )
        .order_by(
            PriceSnapshot.timestamp.desc()
        )
    )


def get_avg_recent_volume(
    db,
    stock_id,
    exclude_today=True,
):
    """
    Calculate average recent historical volume.

    When exclude_today=True, "today" means the current IST calendar day,
    NOT the current UTC calendar day.

    This keeps the demo's volume baseline aligned with Indian trading-session
    semantics.
    """

    snaps = db.scalars(
        select(PriceSnapshot)
        .where(
            PriceSnapshot.stock_id == stock_id
        )
        .order_by(
            PriceSnapshot.timestamp.desc()
        )
        .limit(50)
    ).all()

    if exclude_today:
        today_start_utc = get_today_ist_start_utc()

        snaps = [
            snap
            for snap in snaps
            if snap.timestamp < today_start_utc
        ]

    if not snaps:
        return 1_000_000.0

    return (
        sum(float(snapshot.volume) for snapshot in snaps)
        / len(snaps)
    )


# ---------------------------------------------------------------------------
# RESET
# ---------------------------------------------------------------------------

def cmd_reset():
    """
    Restore the complete deterministic demo baseline.

    Steps:

    1. Remove current-IST-day MOCK snapshots.
    2. Restore Stability Sam.
    3. Restore primary Momentum profile.
    4. Synchronize demo watchlists.
    5. Clear old user view state.
    6. Establish a new previous-view baseline from each stock's final
       remaining historical observation.

    After this command:

        current market state = historical baseline

        last viewed price = historical baseline

    Therefore after `advance`:

        session change
        AND
        since-last-view change

    are both measured from the same deterministic baseline.
    """

    db = SessionLocal()

    try:

        # ------------------------------------------------------------------
        # STEP 1: DELETE CURRENT IST-DAY MOCK OBSERVATIONS
        # ------------------------------------------------------------------

        today_start_utc = get_today_ist_start_utc()

        print()
        print("=== RESETTING DETERMINISTIC DEMO ===")
        print()

        print(
            "Cleaning mock snapshots from current IST day..."
        )

        print(
            f"  IST-day UTC boundary: "
            f"{today_start_utc.isoformat()}"
        )

        deleted = db.execute(
            delete(PriceSnapshot).where(
                PriceSnapshot.source == "mock",
                PriceSnapshot.timestamp >= today_start_utc,
            )
        )

        db.commit()

        print(
            f"  Deleted {deleted.rowcount} "
            "current-session mock snapshot(s)."
        )

        # ------------------------------------------------------------------
        # STEP 2: RESTORE SECOND DEMO IDENTITY
        # ------------------------------------------------------------------

        print()
        print(
            "Ensuring second demo identity "
            "(Stability Sam) exists..."
        )

        ensure_stability_demo_user(db)

        # ------------------------------------------------------------------
        # STEP 3: RESTORE PRIMARY PROFILE
        # ------------------------------------------------------------------

        print()
        print(
            "Resetting primary demo profile..."
        )

        ensure_momentum_demo_profile(db)

        # ------------------------------------------------------------------
        # STEP 4: ESTABLISH VIEW BASELINES
        # ------------------------------------------------------------------

        print()
        print("Establishing deterministic view-state baselines...")

        for uid_str in DEMO_USER_IDS:

            uid = uuid.UUID(uid_str)

            # Remove previous view-state rows.
            #
            # This prevents stale state from:
            # - previous demos
            # - removed stocks
            # - previous detail-page visits

            db.execute(
                delete(UserViewState).where(
                    UserViewState.user_id == uid
                )
            )

            db.commit()

            rows = db.execute(
                select(
                    WatchlistItem,
                    Stock,
                )
                .join(
                    Stock,
                    WatchlistItem.stock_id == Stock.id,
                )
                .where(
                    WatchlistItem.user_id == uid
                )
            ).all()

            now = datetime.now(timezone.utc)

            baseline_count = 0

            print()
            print(f"  User: {uid_str}")

            for _watchlist_item, stock in rows:

                latest = get_latest_snapshot(
                    db,
                    stock.id,
                )

                if latest is None:
                    print(
                        f"    WARNING: {stock.symbol} has "
                        "no historical snapshot; skipping."
                    )

                    continue

                db.add(
                    UserViewState(
                        user_id=uid,
                        stock_id=stock.id,
                        last_viewed_at=now,
                        last_viewed_price=latest.close,
                    )
                )

                baseline_count += 1

                print(
                    f"    {stock.symbol:<12} "
                    f"baseline={float(latest.close):>10.2f} "
                    f"timestamp={latest.timestamp}"
                )

            db.commit()

            print(
                f"  Established view-state baseline for "
                f"{baseline_count} stock(s)."
            )

        # ------------------------------------------------------------------
        # COMPLETE
        # ------------------------------------------------------------------

        print()
        print("=== RESET COMPLETE ===")
        print()

        print(
            "Baseline is now each stock's final historical "
            "observation before the current IST day."
        )

        print(
            "Both demo users have just 'viewed' their "
            "watchlists at those baseline prices."
        )

        print()
        print(
            "Next command:"
        )

        print(
            "  docker compose exec backend "
            "python scripts/demo.py advance"
        )

        print()
        print(
            "IMPORTANT: DEMO_MODE=true should remain enabled "
            "so the background poller cannot overwrite "
            "the deterministic scenario."
        )

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()


# ---------------------------------------------------------------------------
# ADVANCE
# ---------------------------------------------------------------------------

def cmd_advance():
    """
    Inject the fixed deterministic market scenario.

    The move for each stock is calculated relative to the clean historical
    baseline established by reset().

    No scoring is performed here.

    This script writes MARKET OBSERVATIONS only.

    The actual feature extraction, objective scoring and personalization are
    still performed by the normal production application code.
    """

    db = SessionLocal()

    try:

        print()
        print("=== ADVANCING DETERMINISTIC MARKET ===")
        print()

        stocks = {
            stock.symbol: stock
            for stock in db.scalars(
                select(Stock)
            ).all()
        }

        now = datetime.now(timezone.utc)

        applied = []

        for symbol, scenario in SCENARIO.items():

            stock = stocks.get(symbol)

            if stock is None:
                print(
                    f"WARNING: {symbol} not found "
                    "in stocks table; skipping."
                )

                continue

            latest = get_latest_snapshot(
                db,
                stock.id,
            )

            if latest is None:
                print(
                    f"WARNING: {symbol} has no prior "
                    "snapshot; skipping."
                )

                continue

            # --------------------------------------------------------------
            # BASE PRICE
            # --------------------------------------------------------------

            base_price = float(
                latest.close
            )

            # --------------------------------------------------------------
            # NEW PRICE
            # --------------------------------------------------------------

            new_price = round(
                base_price
                * (
                    1
                    + scenario["pct_move"]
                ),
                2,
            )

            # --------------------------------------------------------------
            # HISTORICAL VOLUME BASELINE
            # --------------------------------------------------------------

            avg_volume = get_avg_recent_volume(
                db,
                stock.id,
                exclude_today=True,
            )

            new_volume = int(
                avg_volume
                * scenario["volume_multiplier"]
            )

            # --------------------------------------------------------------
            # CREATE OBSERVATION
            # --------------------------------------------------------------

            snapshot = PriceSnapshot(
                id=uuid.uuid4(),
                stock_id=stock.id,
                timestamp=now,
                open=base_price,
                high=(
                    max(
                        base_price,
                        new_price,
                    )
                    * 1.001
                ),
                low=(
                    min(
                        base_price,
                        new_price,
                    )
                    * 0.999
                ),
                close=new_price,
                volume=new_volume,
                source="mock",
            )

            db.add(snapshot)

            # Calculate the actual rounded movement written to the DB.
            #
            # This may differ by a tiny amount from the configured percentage
            # because prices are rounded to two decimal places.

            actual_move_pct = (
                (
                    new_price
                    - base_price
                )
                / base_price
                * 100
            )

            applied.append(
                (
                    symbol,
                    base_price,
                    new_price,
                    actual_move_pct,
                    new_volume,
                )
            )

        db.commit()

        # ------------------------------------------------------------------
        # OUTPUT
        # ------------------------------------------------------------------

        print("Scenario applied:")
        print()

        print(
            f"{'SYMBOL':<12}"
            f"{'FROM':>12}"
            f"{'TO':>12}"
            f"{'MOVE':>12}"
            f"{'VOLUME':>16}"
        )

        print("-" * 64)

        for (
            symbol,
            base,
            new,
            pct,
            volume,
        ) in applied:

            print(
                f"{symbol:<12}"
                f"{base:>12.2f}"
                f"{new:>12.2f}"
                f"{pct:>+11.2f}%"
                f"{volume:>16,}"
            )

        print()
        print("=== ADVANCE COMPLETE ===")
        print()

        print(
            "The deterministic scenario is now frozen."
        )

        print(
            "With DEMO_MODE=true, the background poller "
            "will not overwrite these observations."
        )

        print()
        print(
            "Refresh /watchlist/changes or the dashboard "
            "to inspect the new ranking."
        )

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    if (
        len(sys.argv) != 2
        or sys.argv[1] not in (
            "reset",
            "advance",
        )
    ):
        print(
            "Usage: python scripts/demo.py "
            "[reset|advance]"
        )

        sys.exit(1)

    command = sys.argv[1]

    if command == "reset":
        cmd_reset()

    elif command == "advance":
        cmd_advance()