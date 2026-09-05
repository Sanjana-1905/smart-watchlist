"""
backend/scripts/demo.py — Deterministic Real-History Replay Demo Controller

Product Principle: SIMULATE THE USER, NOT THE MARKET.
Market data is strictly REAL yfinance data stored in price_snapshots.

Usage:
    docker compose exec backend python scripts/demo.py reset
    docker compose exec backend python scripts/demo.py advance

Timeline (Real History Replay):
    Session A Baseline (e.g. 2026-09-03):
        USER LAST CHECKED HERE
        (UserViewState.last_viewed_price = Session A price)

    Session B Evaluated (e.g. 2026-09-04):
        REAL yfinance price snapshot evaluated by feature & attention engines.

    TODAY:
        Session B close vs Session A close

    SINCE CHECKED:
        Session B close vs UserViewState.last_viewed_price

    Personalization:
        Same REAL market facts.
        Different user profiles
        (MOMENTUM vs STABILITY)
        -> different personal relevance and final attention score.
"""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


# ---------------------------------------------------------------------------
# Make backend package importable when this script is run directly
# ---------------------------------------------------------------------------

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
from app.repositories import (
    stock_repository,
    view_state_repository,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

IST = ZoneInfo("Asia/Kolkata")


PRIMARY_DEMO_USER_ID = (
    "00000000-0000-0000-0000-000000000001"
)

STABILITY_DEMO_USER_ID = (
    "00000000-0000-0000-0000-000000000002"
)


DEMO_USER_IDS = [
    PRIMARY_DEMO_USER_ID,
    STABILITY_DEMO_USER_ID,
]


PRIMARY_DEMO_EMAIL = (
    "demo@smartwatchlist.dev"
)

PRIMARY_DEMO_PASSWORD = (
    "demo1234"
)

PRIMARY_DEMO_DISPLAY_NAME = (
    "Primary Demo User"
)


STABILITY_DEMO_EMAIL = (
    "demo.stability@smartwatchlist.dev"
)

STABILITY_DEMO_PASSWORD = (
    "demo1234"
)

STABILITY_DEMO_DISPLAY_NAME = (
    "Stability Sam"
)


# ---------------------------------------------------------------------------
# Demo watchlist
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Real historical replay dates
# ---------------------------------------------------------------------------

BASELINE_SESSION_DATE = "2026-09-03"
EVALUATED_SESSION_DATE = "2026-09-04"


# ===========================================================================
# DEMO USER BOOTSTRAP
# ===========================================================================

def ensure_demo_users(db):
    """
    Ensure both deterministic demo users, profiles,
    and required watchlist memberships exist.

    IMPORTANT:

    On a completely fresh database, User rows must
    exist BEFORE UserProfile rows are inserted.

    Therefore both User objects are added and flushed
    before creating the profiles.

    This fixes the fresh-clone ForeignKeyViolation:

        user_profiles.user_id
        -> users.id
    """

    p_uid = uuid.UUID(
        PRIMARY_DEMO_USER_ID
    )

    s_uid = uuid.UUID(
        STABILITY_DEMO_USER_ID
    )

    # ------------------------------------------------------------------
    # 1. PRIMARY DEMO USER
    # ------------------------------------------------------------------

    p_user = db.get(
        User,
        p_uid,
    )

    if p_user is None:

        p_user = User(
            id=p_uid,
            email=PRIMARY_DEMO_EMAIL,
            password_hash=hash_password(
                PRIMARY_DEMO_PASSWORD
            ),
            display_name=(
                PRIMARY_DEMO_DISPLAY_NAME
            ),
        )

        db.add(p_user)

    else:

        p_user.email = (
            PRIMARY_DEMO_EMAIL
        )

        p_user.display_name = (
            PRIMARY_DEMO_DISPLAY_NAME
        )

        p_user.password_hash = (
            hash_password(
                PRIMARY_DEMO_PASSWORD
            )
        )

    # ------------------------------------------------------------------
    # 2. STABILITY DEMO USER
    # ------------------------------------------------------------------

    s_user = db.get(
        User,
        s_uid,
    )

    if s_user is None:

        s_user = User(
            id=s_uid,
            email=STABILITY_DEMO_EMAIL,
            password_hash=hash_password(
                STABILITY_DEMO_PASSWORD
            ),
            display_name=(
                STABILITY_DEMO_DISPLAY_NAME
            ),
        )

        db.add(s_user)

    else:

        s_user.email = (
            STABILITY_DEMO_EMAIL
        )

        s_user.display_name = (
            STABILITY_DEMO_DISPLAY_NAME
        )

        s_user.password_hash = (
            hash_password(
                STABILITY_DEMO_PASSWORD
            )
        )

    # ------------------------------------------------------------------
    # CRITICAL FRESH-DATABASE FIX
    #
    # Force both parent User rows into PostgreSQL before
    # inserting UserProfile rows that reference them.
    #
    # flush() does NOT commit the transaction.
    # ------------------------------------------------------------------

    db.flush()

    # ------------------------------------------------------------------
    # 3. PRIMARY PROFILE
    # ------------------------------------------------------------------

    p_prof = db.get(
        UserProfile,
        p_uid,
    )

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

        p_prof.risk_profile = (
            "AGGRESSIVE"
        )

        p_prof.attention_style = (
            "MOMENTUM"
        )

        p_prof.time_horizon = (
            "SHORT_TERM"
        )

        p_prof.onboarding_completed = (
            True
        )

    # ------------------------------------------------------------------
    # 4. STABILITY PROFILE
    # ------------------------------------------------------------------

    s_prof = db.get(
        UserProfile,
        s_uid,
    )

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

        s_prof.risk_profile = (
            "CONSERVATIVE"
        )

        s_prof.attention_style = (
            "STABILITY"
        )

        s_prof.time_horizon = (
            "LONG_TERM"
        )

        s_prof.onboarding_completed = (
            True
        )

    # Commit users + profiles together
    db.commit()

    # ------------------------------------------------------------------
    # 5. SYNCHRONIZE DEMO WATCHLIST
    # ------------------------------------------------------------------

    now = datetime.now(
        timezone.utc
    )

    for uid in (
        p_uid,
        s_uid,
    ):

        existing_items = (
            db.scalars(
                select(
                    WatchlistItem
                ).where(
                    WatchlistItem.user_id
                    == uid
                )
            )
            .all()
        )

        existing_stock_ids = {
            item.stock_id
            for item in existing_items
        }

        for symbol in DEMO_WATCHLIST:

            stock = (
                stock_repository
                .get_by_symbol(
                    db,
                    symbol,
                )
            )

            # If catalog import has not created
            # this stock yet, do not fabricate it.
            if stock is None:
                continue

            if (
                stock.id
                in existing_stock_ids
            ):
                continue

            db.add(
                WatchlistItem(
                    id=uuid.uuid4(),
                    user_id=uid,
                    stock_id=stock.id,
                    added_at=now,
                    version=1,
                )
            )

            # Prevent duplicate insertion inside
            # this same synchronization pass.
            existing_stock_ids.add(
                stock.id
            )

    db.commit()


# ===========================================================================
# HISTORICAL SNAPSHOT HELPER
# ===========================================================================

def get_snapshot_for_date(
    db,
    stock_id,
    target_date_str,
):
    """
    Fetch a real PriceSnapshot for a given
    IST date string (YYYY-MM-DD).

    If multiple observations exist on the same
    IST day, use the latest timestamp from that day.
    """

    snapshots = (
        stock_repository.get_history(
            db,
            stock_id,
        )
    )

    matching = []

    for snapshot in snapshots:

        if snapshot.timestamp is None:
            continue

        ts_ist = (
            snapshot.timestamp
            .astimezone(IST)
        )

        if (
            ts_ist.strftime(
                "%Y-%m-%d"
            )
            == target_date_str
        ):
            matching.append(
                snapshot
            )

    if not matching:
        return None

    return max(
        matching,
        key=lambda snapshot:
            snapshot.timestamp,
    )


# ===========================================================================
# RESET
# ===========================================================================

def cmd_reset():
    """
    Reset user baselines to historical Session A.

    This simulates:

        "Both users last checked the market
         at Session A."

    Market data itself is never fabricated.
    """

    db = SessionLocal()

    try:

        print(
            "\n"
            + "=" * 70
        )

        print(
            "RESETTING DEMO: "
            "REAL-HISTORY REPLAY "
            f"(BASELINE = "
            f"{BASELINE_SESSION_DATE})"
        )

        print(
            "=" * 70
        )

        # --------------------------------------------------------------
        # Remove legacy mock observations.
        #
        # Real yfinance data remains untouched.
        # --------------------------------------------------------------

        db.execute(
            delete(
                PriceSnapshot
            ).where(
                PriceSnapshot.source
                == "mock"
            )
        )

        db.commit()

        # --------------------------------------------------------------
        # Ensure demo identities and watchlists exist.
        # --------------------------------------------------------------

        ensure_demo_users(db)

        p_uid = uuid.UUID(
            PRIMARY_DEMO_USER_ID
        )

        s_uid = uuid.UUID(
            STABILITY_DEMO_USER_ID
        )

        print()

        print(
            "Setting user view-state "
            "baselines to Session A "
            f"({BASELINE_SESSION_DATE}):"
        )

        print(
            f"{'SYMBOL':<12} "
            f"{'BASELINE PRICE':>18} "
            f"{'EVALUATED PRICE':>20} "
            f"{'MOVE %':>10}"
        )

        print(
            "-" * 68
        )

        # --------------------------------------------------------------
        # Establish Session A user baselines.
        # --------------------------------------------------------------

        for symbol in DEMO_WATCHLIST:

            stock = (
                stock_repository
                .get_by_symbol(
                    db,
                    symbol,
                )
            )

            if not stock:
                continue

            snap_a = (
                get_snapshot_for_date(
                    db,
                    stock.id,
                    BASELINE_SESSION_DATE,
                )
            )

            snap_b = (
                get_snapshot_for_date(
                    db,
                    stock.id,
                    EVALUATED_SESSION_DATE,
                )
            )

            # ----------------------------------------------------------
            # Fallback:
            #
            # If exact demo dates are not available,
            # use latest two REAL persisted snapshots.
            #
            # No synthetic prices are created.
            # ----------------------------------------------------------

            if (
                snap_a is None
                or snap_b is None
            ):

                history = (
                    stock_repository
                    .get_history(
                        db,
                        stock.id,
                    )
                )

                if len(history) >= 2:

                    snap_a = history[-2]
                    snap_b = history[-1]

                elif len(history) == 1:

                    snap_a = history[0]
                    snap_b = history[0]

            if snap_a is None:
                continue

            price_a = float(
                snap_a.close
            )

            price_b = (
                float(
                    snap_b.close
                )
                if snap_b
                else price_a
            )

            move_pct = (
                (
                    price_b
                    / price_a
                    - 1
                )
                * 100
                if price_a > 0
                else 0.0
            )

            # ----------------------------------------------------------
            # Both demo users receive the SAME market baseline.
            #
            # This is intentional:
            #
            # SAME MARKET
            # DIFFERENT PROFILE
            # -> different personal relevance
            # ----------------------------------------------------------

            for uid in (
                p_uid,
                s_uid,
            ):

                view_state_repository.upsert(
                    db,
                    uid,
                    stock.id,
                    price_a,
                    snap_a.timestamp,
                )

            print(
                f"{symbol:<12} "
                f"{price_a:>18.2f} "
                f"{price_b:>20.2f} "
                f"{move_pct:>+9.2f}%"
            )

        # Ensure all baseline changes are persisted.
        db.commit()

        print(
            "-" * 68
        )

        print(
            "Demo reset successfully!"
        )

        print(
            "Both demo users are set "
            "to the historical Session A baseline."
        )

        print(
            "Market observations were NOT modified."
        )

        print(
            "Market data remains real persisted "
            "yfinance history."
        )

        print(
            "=" * 70
            + "\n"
        )

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()


# ===========================================================================
# ADVANCE / MARK CAUGHT UP
# ===========================================================================

def cmd_advance():
    """
    Mark both demo users as caught up to the
    latest persisted market observation for
    every stock they currently watch.

    Important:
        - Does NOT modify market data.
        - Does NOT fabricate prices.
        - Only updates UserViewState.
        - Uses ACTUAL persisted watchlists.
    """

    db = SessionLocal()

    try:

        print(
            "\n"
            + "=" * 70
        )

        print(
            "ADVANCING DEMO: "
            "MARKING DEMO USERS CAUGHT UP"
        )

        print(
            "=" * 70
        )

        ensure_demo_users(db)

        p_uid = uuid.UUID(
            PRIMARY_DEMO_USER_ID
        )

        s_uid = uuid.UUID(
            STABILITY_DEMO_USER_ID
        )

        demo_user_ids = (
            p_uid,
            s_uid,
        )

        # --------------------------------------------------------------
        # Use UNION of stocks ACTUALLY watched
        # by the two demo users.
        #
        # This avoids the earlier bug where stocks
        # added outside DEMO_WATCHLIST retained
        # stale baselines.
        # --------------------------------------------------------------

        rows = (
            db.query(
                Stock
            )
            .join(
                WatchlistItem,
                WatchlistItem.stock_id
                == Stock.id,
            )
            .filter(
                WatchlistItem.user_id.in_(
                    demo_user_ids
                )
            )
            .distinct()
            .order_by(
                Stock.symbol
            )
            .all()
        )

        print()

        print(
            "Updating demo user "
            "view-state baselines "
            "to latest real observations:"
        )

        print(
            f"{'SYMBOL':<14}"
            f"{'LATEST PRICE':>16}"
            f"{'OBSERVED AT':>28}"
            f"{'SOURCE':>14}"
        )

        print(
            "-" * 72
        )

        updated = 0
        skipped = 0

        for stock in rows:

            # ----------------------------------------------------------
            # Latest persisted observation.
            #
            # We deliberately do not generate or mutate
            # market prices here.
            # ----------------------------------------------------------

            latest = (
                db.query(
                    PriceSnapshot
                )
                .filter(
                    PriceSnapshot.stock_id
                    == stock.id
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

            price = float(
                latest.close
            )

            # ----------------------------------------------------------
            # Update only demo users who actually
            # watch this particular stock.
            # ----------------------------------------------------------

            for uid in demo_user_ids:

                watches_stock = (
                    db.query(
                        WatchlistItem
                    )
                    .filter(
                        WatchlistItem.user_id
                        == uid,
                        WatchlistItem.stock_id
                        == stock.id,
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

        print(
            "-" * 72
        )

        print()

        print(
            f"Demo advanced successfully: "
            f"{updated} user/stock "
            f"baseline(s) updated."
        )

        if skipped:

            print(
                f"{skipped} stock(s) skipped "
                "because no persisted market "
                "observation exists."
            )

        print(
            "Since-checked returns should now "
            "be 0% for every updated watched stock."
        )

        print(
            "Market observations were NOT modified."
        )

        print(
            "=" * 70
            + "\n"
        )

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()


# ===========================================================================
# CLI
# ===========================================================================

if __name__ == "__main__":

    if (
        len(sys.argv) < 2
        or sys.argv[1]
        not in (
            "reset",
            "advance",
        )
    ):

        print(
            "Usage: "
            "python scripts/demo.py "
            "[reset|advance]"
        )

        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "reset":

        cmd_reset()

    elif cmd == "advance":

        cmd_advance()