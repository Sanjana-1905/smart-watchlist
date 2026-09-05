"""
Deterministic Smart Watchlist demo controller.

Usage:
    docker compose exec backend python scripts/demo.py reset
    docker compose exec backend python scripts/demo.py advance

Timeline:

    Previous trading-session close
              |
              | small market move
              v
    Intermediate observation
       USER LAST CHECKED HERE
              |
              | later market movement
              v
    Final observation

Therefore:

    TODAY
        = final price vs previous trading-session close

    SINCE CHECKED
        = final price vs intermediate last-view price

The two values are intentionally different.

IMPORTANT:
    Run with DEMO_MODE=true so the APScheduler market poller does not
    overwrite the deterministic scenario.
"""

import sys
import uuid
from collections import defaultdict
from datetime import datetime, timezone, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# ---------------------------------------------------------------------------
# IMPORT PATH
# ---------------------------------------------------------------------------

# Host:
#   <repo>/backend/scripts/demo.py
#   <repo>/backend/app/
#
# Docker:
#   /app/scripts/demo.py
#   /app/app/
#
# In both environments, backend root = parent of scripts/.
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


# ===========================================================================
# GENERAL CONFIG
# ===========================================================================

IST = ZoneInfo("Asia/Kolkata")


# ===========================================================================
# DEMO USERS
# ===========================================================================

PRIMARY_DEMO_USER_ID = "00000000-0000-0000-0000-000000000001"
STABILITY_DEMO_USER_ID = "00000000-0000-0000-0000-000000000002"

DEMO_USER_IDS = [
    PRIMARY_DEMO_USER_ID,
    STABILITY_DEMO_USER_ID,
]

PRIMARY_DEMO_EMAIL = "demo@smartwatchlist.dev"

STABILITY_DEMO_EMAIL = "demo.stability@smartwatchlist.dev"
STABILITY_DEMO_PASSWORD = "demo1234"
STABILITY_DEMO_DISPLAY_NAME = "Stability Sam"


# ===========================================================================
# DEMO MARKET SCENARIO
# ===========================================================================

# Stage 1:
# Small movement from previous session close to the point where the user
# last checked the watchlist.
#
# These are deliberately mild.
SCENARIO_INTERMEDIATE = {
    "RELIANCE": 0.015,     # +1.50%
    "BEL": 0.008,          # +0.80%
    "HDFCBANK": -0.010,    # -1.00%
    "TCS": 0.002,          # +0.20%
    "TATASTEEL": -0.003,   # -0.30%
}


# Stage 2:
# Additional movement AFTER the user checked.
#
# pct_move here is relative to the intermediate/check price.
SCENARIO_FINAL = {
    "RELIANCE": {
        "pct_move": 0.047,         # +4.70% since checked
        "volume_multiplier": 3.1,
    },
    "BEL": {
        "pct_move": 0.033,         # +3.30% since checked
        "volume_multiplier": 2.3,
    },
    "HDFCBANK": {
        "pct_move": -0.028,        # -2.80% since checked
        "volume_multiplier": 1.9,
    },
    "TCS": {
        "pct_move": 0.002,         # +0.20% since checked
        "volume_multiplier": 1.05,
    },
    "TATASTEEL": {
        "pct_move": -0.003,        # -0.30% since checked
        "volume_multiplier": 0.95,
    },
}


# The feature engine calculates current-session volume as the SUM of all
# snapshots in the session.
#
# Give 20% of the target day's volume to the intermediate observation and
# the remaining 80% to the final observation.
INTERMEDIATE_VOLUME_FRACTION = 0.20


# ===========================================================================
# TIME HELPERS
# ===========================================================================

def get_today_ist_start_utc() -> datetime:
    """
    Return the UTC timestamp corresponding to today's midnight in IST.

    Example:
        2026-09-05 00:00 IST
        =
        2026-09-04 18:30 UTC

    PostgreSQL timestamps are stored in UTC, but market sessions are grouped
    using Indian calendar dates.
    """

    now_ist = datetime.now(IST)

    start_ist = datetime.combine(
        now_ist.date(),
        time.min,
        tzinfo=IST,
    )

    return start_ist.astimezone(timezone.utc)


def get_intermediate_timestamp() -> datetime:
    """
    Return a deterministic-safe timestamp representing when the user
    last checked.

    Normally this is 10 minutes ago.

    Unlike a hard-coded "10:30 AM today", this can never accidentally point
    into the future when the demo is run early in the morning.
    """

    now_utc = datetime.now(timezone.utc)
    today_start_utc = get_today_ist_start_utc()

    candidate = now_utc - timedelta(minutes=10)
    earliest_today = today_start_utc + timedelta(minutes=1)

    return max(candidate, earliest_today)


# ===========================================================================
# MARKET HELPERS
# ===========================================================================

def get_latest_snapshot(db, stock_id):
    """Return the latest stored observation for a stock."""

    return db.scalar(
        select(PriceSnapshot)
        .where(
            PriceSnapshot.stock_id == stock_id
        )
        .order_by(
            PriceSnapshot.timestamp.desc()
        )
    )


def get_previous_session_close(db, stock_id):
    """
    Return the newest observation strictly before today's IST session.

    This is the baseline used for the TODAY percentage.
    """

    today_start_utc = get_today_ist_start_utc()

    return db.scalar(
        select(PriceSnapshot)
        .where(
            PriceSnapshot.stock_id == stock_id,
            PriceSnapshot.timestamp < today_start_utc,
        )
        .order_by(
            PriceSnapshot.timestamp.desc()
        )
    )


def get_historical_snapshots_before_today(db, stock_id):
    """
    Return all observations prior to today's IST session.
    """

    today_start_utc = get_today_ist_start_utc()

    return db.scalars(
        select(PriceSnapshot)
        .where(
            PriceSnapshot.stock_id == stock_id,
            PriceSnapshot.timestamp < today_start_utc,
        )
        .order_by(
            PriceSnapshot.timestamp.asc()
        )
    ).all()


def get_historical_session_volumes(db, stock_id):
    """
    Convert historical raw snapshots into daily IST trading-session volumes.

    The production feature engine treats a session's volume as the SUM of
    snapshot volumes in that session, so the demo must use the same model.
    """

    snapshots = get_historical_snapshots_before_today(
        db,
        stock_id,
    )

    grouped = defaultdict(float)

    for snapshot in snapshots:
        timestamp = snapshot.timestamp

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(
                tzinfo=timezone.utc
            )

        session_date = timestamp.astimezone(
            IST
        ).date()

        grouped[session_date] += float(
            snapshot.volume
        )

    return [
        grouped[session_date]
        for session_date in sorted(grouped)
    ]


def get_avg_historical_session_volume(db, stock_id) -> float:
    """
    Return average volume from the most recent 20 historical IST sessions.
    """

    volumes = get_historical_session_volumes(
        db,
        stock_id,
    )

    if not volumes:
        return 1_000_000.0

    recent = volumes[-20:]

    return sum(recent) / len(recent)


# ===========================================================================
# DEMO USER HELPERS
# ===========================================================================

def ensure_primary_demo_user_exists(db):
    """
    Ensure the primary seeded demo user exists.
    """

    uid = uuid.UUID(
        PRIMARY_DEMO_USER_ID
    )

    user = db.get(
        User,
        uid,
    )

    if user is None:
        raise RuntimeError(
            "Primary demo user does not exist. "
            "Run the normal application seed/bootstrap first."
        )

    if user.email != PRIMARY_DEMO_EMAIL:
        print(
            "  WARNING: primary demo UUID exists but email is "
            f"{user.email!r}; expected {PRIMARY_DEMO_EMAIL!r}"
        )


def ensure_momentum_demo_profile(db):
    """
    Force the primary demo profile to:

        AGGRESSIVE
        MOMENTUM
        SHORT_TERM
    """

    uid = uuid.UUID(
        PRIMARY_DEMO_USER_ID
    )

    profile = db.get(
        UserProfile,
        uid,
    )

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
            "  Created primary profile: "
            "AGGRESSIVE / MOMENTUM / SHORT_TERM"
        )

    else:

        profile.risk_profile = "AGGRESSIVE"
        profile.attention_style = "MOMENTUM"
        profile.time_horizon = "SHORT_TERM"
        profile.onboarding_completed = True
        profile.version += 1

        print(
            "  Reset primary profile: "
            "AGGRESSIVE / MOMENTUM / SHORT_TERM"
        )

    db.commit()


def ensure_stability_demo_user(db):
    """
    Create/reset Stability Sam.

    Stability Sam has the exact same watchlist and market observations as
    the primary user, but:

        CONSERVATIVE
        STABILITY
        LONG_TERM
    """

    uid = uuid.UUID(
        STABILITY_DEMO_USER_ID
    )

    primary_uid = uuid.UUID(
        PRIMARY_DEMO_USER_ID
    )

    # ----------------------------------------------------------------------
    # USER
    # ----------------------------------------------------------------------

    user = db.get(
        User,
        uid,
    )

    if user is None:

        user = User(
            id=uid,
            email=STABILITY_DEMO_EMAIL,
            password_hash=hash_password(
                STABILITY_DEMO_PASSWORD
            ),
            display_name=STABILITY_DEMO_DISPLAY_NAME,
        )

        db.add(user)
        db.commit()

        print(
            f"  Created {STABILITY_DEMO_EMAIL}"
        )

    else:

        # Keep the deterministic display identity self-healing.
        user.email = STABILITY_DEMO_EMAIL
        user.display_name = STABILITY_DEMO_DISPLAY_NAME

        # Ensure the documented demo password works after any manual tests.
        user.password_hash = hash_password(
            STABILITY_DEMO_PASSWORD
        )

        db.commit()

        print(
            f"  Reset user {STABILITY_DEMO_EMAIL}"
        )

    # ----------------------------------------------------------------------
    # PROFILE
    # ----------------------------------------------------------------------

    profile = db.get(
        UserProfile,
        uid,
    )

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
            "  Created Stability profile: "
            "CONSERVATIVE / STABILITY / LONG_TERM"
        )

    else:

        profile.risk_profile = "CONSERVATIVE"
        profile.attention_style = "STABILITY"
        profile.time_horizon = "LONG_TERM"
        profile.onboarding_completed = True
        profile.version += 1

        print(
            "  Reset Stability profile: "
            "CONSERVATIVE / STABILITY / LONG_TERM"
        )

    db.commit()

    # ----------------------------------------------------------------------
    # EXACT WATCHLIST SYNCHRONIZATION
    # ----------------------------------------------------------------------

    primary_items = db.scalars(
        select(WatchlistItem)
        .where(
            WatchlistItem.user_id == primary_uid
        )
    ).all()

    primary_stock_ids = {
        item.stock_id
        for item in primary_items
    }

    stability_items = db.scalars(
        select(WatchlistItem)
        .where(
            WatchlistItem.user_id == uid
        )
    ).all()

    stability_stock_ids = {
        item.stock_id
        for item in stability_items
    }

    missing = (
        primary_stock_ids
        - stability_stock_ids
    )

    extras = (
        stability_stock_ids
        - primary_stock_ids
    )

    now = datetime.now(
        timezone.utc
    )

    for stock_id in missing:

        db.add(
            WatchlistItem(
                id=uuid.uuid4(),
                user_id=uid,
                stock_id=stock_id,
                added_at=now,
                version=1,
            )
        )

    if extras:

        db.execute(
            delete(WatchlistItem)
            .where(
                WatchlistItem.user_id == uid,
                WatchlistItem.stock_id.in_(
                    extras
                ),
            )
        )

    db.commit()

    print(
        "  Stability watchlist synchronized: "
        f"{len(primary_stock_ids)} stock(s) "
        f"({len(missing)} added, {len(extras)} removed)"
    )


# ===========================================================================
# RESET
# ===========================================================================

def cmd_reset():
    """
    Reset the deterministic demo to the moment the users last checked.

    Result:

        previous session close
                |
                | mild movement
                v
        intermediate price
                ^
                |
           USER VIEWED HERE

    The `advance` command later creates the final market state.
    """

    db = SessionLocal()

    try:

        print()
        print("=" * 78)
        print("RESETTING SMART WATCHLIST DETERMINISTIC DEMO")
        print("=" * 78)
        print()

        today_start_utc = (
            get_today_ist_start_utc()
        )

        # ------------------------------------------------------------------
        # STEP 1 — CLEAN CURRENT SESSION MOCK DATA
        # ------------------------------------------------------------------

        print(
            "1. Cleaning current IST-day mock observations..."
        )

        deleted = db.execute(
            delete(PriceSnapshot)
            .where(
                PriceSnapshot.source == "mock",
                PriceSnapshot.timestamp
                >= today_start_utc,
            )
        )

        db.commit()

        print(
            f"   Deleted {deleted.rowcount} snapshot(s)"
        )

        # ------------------------------------------------------------------
        # STEP 2 — RESTORE USERS
        # ------------------------------------------------------------------

        print()
        print(
            "2. Restoring deterministic demo identities..."
        )

        ensure_primary_demo_user_exists(
            db
        )

        ensure_momentum_demo_profile(
            db
        )

        ensure_stability_demo_user(
            db
        )

        # ------------------------------------------------------------------
        # STEP 3 — CREATE INTERMEDIATE MARKET STATE
        # ------------------------------------------------------------------

        print()
        print(
            "3. Creating intermediate market state "
            "(the users' last-check point)..."
        )

        stocks = {
            stock.symbol: stock
            for stock in db.scalars(
                select(Stock)
            ).all()
        }

        intermediate_timestamp = (
            get_intermediate_timestamp()
        )

        print(
            "   Last-check timestamp: "
            f"{intermediate_timestamp.astimezone(IST).isoformat()}"
        )

        intermediate_prices = {}

        print()
        print(
            f"{'SYMBOL':<12}"
            f"{'PREV CLOSE':>14}"
            f"{'CHECKED':>14}"
            f"{'TODAY@CHECK':>15}"
        )

        print("-" * 55)

        for (
            symbol,
            pct_move,
        ) in SCENARIO_INTERMEDIATE.items():

            stock = stocks.get(
                symbol
            )

            if stock is None:
                print(
                    f"WARNING: {symbol} not found; skipping"
                )
                continue

            historical = (
                get_previous_session_close(
                    db,
                    stock.id,
                )
            )

            if historical is None:
                print(
                    f"WARNING: {symbol} has no previous "
                    "session close; skipping"
                )
                continue

            previous_close = float(
                historical.close
            )

            intermediate_price = round(
                previous_close
                * (
                    1
                    + pct_move
                ),
                2,
            )

            # --------------------------------------------------------------
            # SESSION VOLUME
            # --------------------------------------------------------------

            avg_volume = (
                get_avg_historical_session_volume(
                    db,
                    stock.id,
                )
            )

            final_multiplier = (
                SCENARIO_FINAL[
                    symbol
                ][
                    "volume_multiplier"
                ]
            )

            desired_total_volume = int(
                avg_volume
                * final_multiplier
            )

            intermediate_volume = max(
                int(
                    desired_total_volume
                    * INTERMEDIATE_VOLUME_FRACTION
                ),
                1,
            )

            snapshot = PriceSnapshot(
                id=uuid.uuid4(),
                stock_id=stock.id,
                timestamp=intermediate_timestamp,
                open=previous_close,
                high=(
                    max(
                        previous_close,
                        intermediate_price,
                    )
                    * 1.001
                ),
                low=(
                    min(
                        previous_close,
                        intermediate_price,
                    )
                    * 0.999
                ),
                close=intermediate_price,
                volume=intermediate_volume,
                source="mock",
            )

            db.add(snapshot)

            intermediate_prices[
                stock.id
            ] = intermediate_price

            today_at_check = (
                (
                    intermediate_price
                    / previous_close
                )
                - 1
            ) * 100

            print(
                f"{symbol:<12}"
                f"{previous_close:>14.2f}"
                f"{intermediate_price:>14.2f}"
                f"{today_at_check:>+14.2f}%"
            )

        db.commit()

        # ------------------------------------------------------------------
        # STEP 4 — SAVE LAST VIEW STATE
        # ------------------------------------------------------------------

        print()
        print(
            "4. Saving intermediate prices as "
            "'last checked' state..."
        )

        for uid_str in DEMO_USER_IDS:

            uid = uuid.UUID(
                uid_str
            )

            db.execute(
                delete(UserViewState)
                .where(
                    UserViewState.user_id
                    == uid
                )
            )

            rows = db.execute(
                select(
                    WatchlistItem,
                    Stock,
                )
                .join(
                    Stock,
                    WatchlistItem.stock_id
                    == Stock.id,
                )
                .where(
                    WatchlistItem.user_id
                    == uid
                )
            ).all()

            count = 0

            for _item, stock in rows:

                intermediate_price = (
                    intermediate_prices.get(
                        stock.id
                    )
                )

                if intermediate_price is None:
                    continue

                db.add(
                    UserViewState(
                        user_id=uid,
                        stock_id=stock.id,
                        last_viewed_at=intermediate_timestamp,
                        last_viewed_price=intermediate_price,
                    )
                )

                count += 1

            db.commit()

            print(
                f"   {uid_str}: "
                f"{count} view baseline(s)"
            )

        print()
        print("=" * 78)
        print("RESET COMPLETE")
        print("=" * 78)
        print()

        print(
            "The database now represents the moment "
            "both demo users last checked."
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
            "Keep DEMO_MODE=true so the background "
            "poller cannot mutate the scenario."
        )

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()


# ===========================================================================
# ADVANCE
# ===========================================================================

def cmd_advance():
    """
    Advance the market from the persisted last-check state.

    IMPORTANT:
    This is safe to run repeatedly.

    Final prices are ALWAYS computed from UserViewState.last_viewed_price,
    not whatever the latest database observation happens to be.

    Any prior final snapshots after the user's last-view timestamp are
    removed first.

    Therefore repeated calls do not compound the market movement.
    """

    db = SessionLocal()

    try:

        print()
        print("=" * 78)
        print("ADVANCING MARKET TO FINAL DEMO STATE")
        print("=" * 78)
        print()

        primary_uid = uuid.UUID(
            PRIMARY_DEMO_USER_ID
        )

        stocks = {
            stock.symbol: stock
            for stock in db.scalars(
                select(Stock)
            ).all()
        }

        applied = []

        for (
            symbol,
            scenario,
        ) in SCENARIO_FINAL.items():

            stock = stocks.get(
                symbol
            )

            if stock is None:
                print(
                    f"WARNING: {symbol} not found; skipping"
                )
                continue

            # --------------------------------------------------------------
            # READ LAST-CHECKED BASELINE
            # --------------------------------------------------------------

            view_state = db.get(
                UserViewState,
                {
                    "user_id": primary_uid,
                    "stock_id": stock.id,
                },
            )

            if view_state is None:

                raise RuntimeError(
                    f"{symbol}: no demo view-state exists. "
                    "Run `python scripts/demo.py reset` first."
                )

            intermediate_price = float(
                view_state.last_viewed_price
            )

            intermediate_timestamp = (
                view_state.last_viewed_at
            )

            if intermediate_timestamp.tzinfo is None:

                intermediate_timestamp = (
                    intermediate_timestamp.replace(
                        tzinfo=timezone.utc
                    )
                )

            # --------------------------------------------------------------
            # DELETE ANY OLD FINAL DEMO SNAPSHOT
            # --------------------------------------------------------------

            db.execute(
                delete(PriceSnapshot)
                .where(
                    PriceSnapshot.stock_id
                    == stock.id,

                    PriceSnapshot.source
                    == "mock",

                    PriceSnapshot.timestamp
                    > intermediate_timestamp,
                )
            )

            # --------------------------------------------------------------
            # FINAL PRICE
            # --------------------------------------------------------------

            final_price = round(
                intermediate_price
                * (
                    1
                    + scenario[
                        "pct_move"
                    ]
                ),
                2,
            )

            # --------------------------------------------------------------
            # FINAL SESSION VOLUME
            # --------------------------------------------------------------

            avg_historical_volume = (
                get_avg_historical_session_volume(
                    db,
                    stock.id,
                )
            )

            target_total_volume = int(
                avg_historical_volume
                * scenario[
                    "volume_multiplier"
                ]
            )

            intermediate_snapshot = db.scalar(
                select(PriceSnapshot)
                .where(
                    PriceSnapshot.stock_id
                    == stock.id,

                    PriceSnapshot.source
                    == "mock",

                    PriceSnapshot.timestamp
                    == intermediate_timestamp,
                )
            )

            if intermediate_snapshot is None:

                raise RuntimeError(
                    f"{symbol}: intermediate demo snapshot "
                    "is missing. Run reset first."
                )

            intermediate_volume = int(
                intermediate_snapshot.volume
            )

            final_volume = max(
                target_total_volume
                - intermediate_volume,
                1,
            )

            # --------------------------------------------------------------
            # FINAL TIMESTAMP
            # --------------------------------------------------------------

            final_timestamp = datetime.now(
                timezone.utc
            )

            # Extremely defensive:
            # ensure the final row is always later than the last-view row.
            if final_timestamp <= intermediate_timestamp:

                final_timestamp = (
                    intermediate_timestamp
                    + timedelta(minutes=1)
                )

            # --------------------------------------------------------------
            # CREATE FINAL OBSERVATION
            # --------------------------------------------------------------

            snapshot = PriceSnapshot(
                id=uuid.uuid4(),
                stock_id=stock.id,
                timestamp=final_timestamp,
                open=intermediate_price,
                high=(
                    max(
                        intermediate_price,
                        final_price,
                    )
                    * 1.001
                ),
                low=(
                    min(
                        intermediate_price,
                        final_price,
                    )
                    * 0.999
                ),
                close=final_price,
                volume=final_volume,
                source="mock",
            )

            db.add(snapshot)

            # --------------------------------------------------------------
            # EXPECTED VALUES
            # --------------------------------------------------------------

            previous_snapshot = (
                get_previous_session_close(
                    db,
                    stock.id,
                )
            )

            if previous_snapshot is None:

                raise RuntimeError(
                    f"{symbol}: previous session "
                    "close missing"
                )

            previous_close = float(
                previous_snapshot.close
            )

            today_pct = (
                (
                    final_price
                    / previous_close
                )
                - 1
            ) * 100

            since_checked_pct = (
                (
                    final_price
                    / intermediate_price
                )
                - 1
            ) * 100

            applied.append(
                (
                    symbol,
                    previous_close,
                    intermediate_price,
                    final_price,
                    today_pct,
                    since_checked_pct,
                    target_total_volume,
                )
            )

        db.commit()

        # ------------------------------------------------------------------
        # OUTPUT
        # ------------------------------------------------------------------

        print(
            f"{'SYMBOL':<12}"
            f"{'PREV':>11}"
            f"{'CHECKED':>11}"
            f"{'NOW':>11}"
            f"{'TODAY':>12}"
            f"{'SINCE':>12}"
        )

        print("-" * 70)

        for (
            symbol,
            previous,
            checked,
            final,
            today_pct,
            since_pct,
            _volume,
        ) in applied:

            print(
                f"{symbol:<12}"
                f"{previous:>11.2f}"
                f"{checked:>11.2f}"
                f"{final:>11.2f}"
                f"{today_pct:>+11.2f}%"
                f"{since_pct:>+11.2f}%"
            )

        print()
        print("=" * 78)
        print("ADVANCE COMPLETE")
        print("=" * 78)
        print()

        print(
            "Expected UI distinction:"
        )

        print()

        for (
            symbol,
            _previous,
            _checked,
            _final,
            today_pct,
            since_pct,
            _volume,
        ) in applied:

            print(
                f"  {symbol:<12} "
                f"Today {today_pct:+.2f}%   "
                f"Since checked {since_pct:+.2f}%"
            )

        print()
        print(
            "With DEMO_MODE=true this state should "
            "remain unchanged until reset/advance "
            "is intentionally run again."
        )

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()


# ===========================================================================
# ENTRY POINT
# ===========================================================================

if __name__ == "__main__":

    if (
        len(sys.argv) != 2
        or sys.argv[1]
        not in (
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
