"""
import_market_history.py — Populate price_snapshots with REAL yfinance daily OHLCV.

Operates on stocks already present in the ``stocks`` table.  Does NOT create
stocks, modify watchlists, or touch any scoring/feature code.

Usage
-----
    # Single symbol
    python scripts/import_market_history.py --symbol ASIANPAINT --period 1y

    # Entire supported catalog
    python scripts/import_market_history.py --period 1y

    # Dry-run: show what would be fetched without writing
    python scripts/import_market_history.py --period 1y --dry-run

Run inside the backend container so the DATABASE_URL env-var resolves:
    docker compose exec -T backend python scripts/import_market_history.py --symbol ASIANPAINT --period 1y

Design
------
Duplicate identity: (stock_id, date in IST).  Because yfinance returns daily
bars we normalise every timestamp to 15:30 IST (NSE close).  If a row already
exists for that stock+date (regardless of its source), we skip it to avoid
clobbering verified fixture history.

The skip logic means running the importer twice never doubles rows (idempotent).
"""

import argparse
import math
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

# ---------------------------------------------------------------------------
# Path setup — works from both host (backend/scripts/) and Docker (/app/scripts/)
# ---------------------------------------------------------------------------
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

import yfinance as yf
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import PriceSnapshot, Stock

# ---------------------------------------------------------------------------
# IST timezone
# ---------------------------------------------------------------------------
IST = ZoneInfo("Asia/Kolkata")

# NSE market close time used for the canonical daily timestamp.
# Every daily bar is stored at 15:30 IST regardless of the actual close second.
NSE_CLOSE_HOUR = 15
NSE_CLOSE_MINUTE = 30

# ---------------------------------------------------------------------------
# Centralised ticker translation map
#
# Rules:
#   1. For the vast majority of NSE symbols, simply appending ".NS" works.
#   2. Symbols that contain punctuation or differ from the Yahoo Finance ticker
#      must be listed here explicitly.
#   3. Symbols that have NO valid Yahoo Finance NSE ticker are mapped to None
#      so they are skipped with an explanatory message rather than silently
#      failing at download time.
# ---------------------------------------------------------------------------

# Explicit overrides — only entries that differ from "<SYMBOL>.NS"
_TICKER_OVERRIDES: dict[str, str | None] = {
    # NSE symbol          Yahoo Finance ticker
    # M&M: ampersand is preserved — yfinance handles "M&M.NS" correctly
    "M&M":        "M&M.NS",
    # BAJAJ-AUTO: Yahoo Finance preserves the hyphen as "BAJAJ-AUTO.NS"
    # (BAJAJAUT.NS returns 404; the default .NS suffix rule would also work,
    #  but this entry makes the decision explicit and tested)
    "BAJAJ-AUTO": "BAJAJ-AUTO.NS",
}

# Symbols we know to be unavailable on Yahoo Finance NSE feed; set to None
# to skip them gracefully rather than wasting a network call.
_UNSUPPORTED: set[str] = set()


def symbol_to_yahoo_ticker(symbol: str) -> str | None:
    """
    Convert an internal NSE symbol to a Yahoo Finance ticker string.

    Returns None for symbols that are not available on Yahoo Finance.
    """
    if symbol in _UNSUPPORTED:
        return None
    if symbol in _TICKER_OVERRIDES:
        return _TICKER_OVERRIDES[symbol]
    # Default: append .NS
    return f"{symbol}.NS"


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _is_valid_row(row) -> bool:
    """Return True iff the OHLCV values are finite, close > 0, volume >= 0."""
    try:
        o = float(row["Open"])
        h = float(row["High"])
        lo = float(row["Low"])
        c = float(row["Close"])
        v = int(row["Volume"])
    except (TypeError, ValueError, KeyError):
        return False

    # Must all be finite
    for val in (o, h, lo, c):
        if not math.isfinite(val):
            return False

    if c <= 0:
        return False
    if v < 0:
        return False

    return True


def _bar_date_ist(ts) -> date:
    """
    Given a bar's index timestamp (pandas Timestamp, possibly tz-aware or naive),
    return the trading date in IST.

    yfinance daily bars with period="1y" come back indexed by date (not datetime),
    so the index is typically a date-like object; we handle both cases.
    """
    if hasattr(ts, "tzinfo") and ts.tzinfo is not None:
        # tz-aware: convert to IST
        dt = ts.astimezone(IST)
    elif hasattr(ts, "date"):
        # naive datetime or pandas Timestamp
        dt = ts
    else:
        # fallback: treat as naive date
        return ts

    if hasattr(dt, "date"):
        return dt.date()
    return dt


def _canonical_timestamp(trading_date: date) -> datetime:
    """
    Return the canonical tz-aware timestamp for a trading date:
    YYYY-MM-DD 15:30:00+05:30 (NSE close, IST).
    """
    return datetime(
        trading_date.year,
        trading_date.month,
        trading_date.day,
        NSE_CLOSE_HOUR,
        NSE_CLOSE_MINUTE,
        0,
        tzinfo=IST,
    )


# ---------------------------------------------------------------------------
# Duplicate check: by stock_id + date (not exact timestamp)
# ---------------------------------------------------------------------------

def _existing_dates_for_stock(db, stock_id) -> set[date]:
    """
    Return the set of trading *dates* (in IST) for which a PriceSnapshot
    already exists for the given stock.  Used for O(1) duplicate look-up
    inside the per-symbol import loop.
    """
    rows = db.scalars(
        select(PriceSnapshot.timestamp).where(PriceSnapshot.stock_id == stock_id)
    ).all()
    dates: set[date] = set()
    for ts in rows:
        if ts is None:
            continue
        # ts is already a tz-aware datetime (DateTime(timezone=True) column)
        ts_ist = ts.astimezone(IST)
        dates.add(ts_ist.date())
    return dates


# ---------------------------------------------------------------------------
# Per-symbol import
# ---------------------------------------------------------------------------

def import_symbol(
    db,
    stock: Stock,
    period: str,
    dry_run: bool = False,
) -> dict:
    """
    Fetch history for one symbol and write new PriceSnapshot rows.

    Returns a result dict with keys:
        symbol, yahoo_ticker, provider_rows, valid_rows,
        inserted, skipped, failed_reason, date_range
    """
    result = {
        "symbol": stock.symbol,
        "yahoo_ticker": None,
        "provider_rows": 0,
        "valid_rows": 0,
        "inserted": 0,
        "skipped": 0,
        "failed_reason": None,
        "date_range": None,
        "source": "yfinance",
    }

    yahoo_ticker = symbol_to_yahoo_ticker(stock.symbol)
    result["yahoo_ticker"] = yahoo_ticker

    if yahoo_ticker is None:
        result["failed_reason"] = "No Yahoo Finance NSE ticker available"
        return result

    # Fetch
    try:
        ticker = yf.Ticker(yahoo_ticker)
        hist = ticker.history(period=period)
    except Exception as exc:
        result["failed_reason"] = f"yfinance exception: {exc}"
        return result

    if hist is None or hist.empty:
        result["failed_reason"] = "Empty response from yfinance"
        return result

    result["provider_rows"] = len(hist)

    # Load existing dates once for efficient dupe checking
    existing_dates = _existing_dates_for_stock(db, stock.id)

    min_date: date | None = None
    max_date: date | None = None
    inserted = 0
    skipped = 0
    valid_rows = 0

    for ts, row in hist.iterrows():
        if not _is_valid_row(row):
            continue
        valid_rows += 1

        trading_date = _bar_date_ist(ts)
        if isinstance(trading_date, datetime):
            trading_date = trading_date.date()

        # Track date range from valid rows
        if min_date is None or trading_date < min_date:
            min_date = trading_date
        if max_date is None or trading_date > max_date:
            max_date = trading_date

        # Skip if this date already has a snapshot (regardless of source)
        if trading_date in existing_dates:
            skipped += 1
            continue

        if dry_run:
            # Count as would-insert but don't write
            inserted += 1
            existing_dates.add(trading_date)
            continue

        snapshot = PriceSnapshot(
            id=uuid.uuid4(),
            stock_id=stock.id,
            timestamp=_canonical_timestamp(trading_date),
            open=float(row["Open"]),
            high=float(row["High"]),
            low=float(row["Low"]),
            close=float(row["Close"]),
            volume=int(row["Volume"]),
            source="yfinance",
        )
        db.add(snapshot)
        existing_dates.add(trading_date)
        inserted += 1

    if not dry_run and inserted > 0:
        db.commit()

    result["valid_rows"] = valid_rows
    result["inserted"] = inserted
    result["skipped"] = skipped
    if min_date and max_date:
        result["date_range"] = f"{min_date} -> {max_date}"

    return result


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------

def _print_symbol_report(result: dict) -> None:
    sym = result["symbol"]
    ticker = result["yahoo_ticker"] or "N/A"
    print(f"\n{'-'*60}")
    print(f"  {sym} -> {ticker}")
    print(f"  provider rows received : {result['provider_rows']}")
    print(f"  valid rows             : {result['valid_rows']}")
    print(f"  inserted               : {result['inserted']}")
    print(f"  skipped (existing)     : {result['skipped']}")
    if result["failed_reason"]:
        print(f"  FAILED                 : {result['failed_reason']}")
    if result["date_range"]:
        print(f"  date range             : {result['date_range']}")
    print(f"  source                 : {result['source']}")


def _print_totals(results: list[dict]) -> None:
    total_requested = len(results)
    total_successful = sum(1 for r in results if not r["failed_reason"])
    total_failed = sum(1 for r in results if r["failed_reason"])
    total_inserted = sum(r["inserted"] for r in results)
    total_skipped = sum(r["skipped"] for r in results)

    print(f"\n{'='*60}")
    print("  TOTALS")
    print(f"{'='*60}")
    print(f"  requested              : {total_requested}")
    print(f"  successful             : {total_successful}")
    print(f"  failed                 : {total_failed}")
    print(f"  inserted               : {total_inserted}")
    print(f"  skipped (existing)     : {total_skipped}")
    print(f"{'='*60}")

    if total_failed:
        print("\nFailed symbols:")
        for r in results:
            if r["failed_reason"]:
                print(f"  {r['symbol']:15s}  {r['failed_reason']}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description=(
            "Populate price_snapshots with real yfinance daily OHLCV history.\n"
            "Operates only on stocks already present in the stocks table.\n"
            "Idempotent: running twice does NOT duplicate rows."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--symbol",
        metavar="SYMBOL",
        help=(
            "Internal NSE symbol to import (e.g. ASIANPAINT). "
            "Omit to import the complete supported catalog."
        ),
    )
    p.add_argument(
        "--period",
        default="1y",
        metavar="PERIOD",
        help=(
            "yfinance period string: 1mo, 3mo, 6mo, 1y, 2y, 5y, max. "
            "Default: 1y"
        ),
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and validate data but do NOT write to the database.",
    )
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    if args.dry_run:
        print("DRY-RUN mode -- no rows will be written to the database.")

    db = SessionLocal()
    try:
        # Resolve the stock(s) to process
        if args.symbol:
            sym = args.symbol.strip().upper()
            stock = db.scalar(select(Stock).where(Stock.symbol == sym))
            if stock is None:
                print(
                    f"ERROR: Symbol '{sym}' not found in the stocks table.\n"
                    "Run python scripts/import_explore.py first to populate the catalog.",
                    file=sys.stderr,
                )
                return 1
            stocks_to_process = [stock]
        else:
            stocks_to_process = list(db.scalars(select(Stock)).all())
            if not stocks_to_process:
                print(
                    "ERROR: No stocks found in the stocks table.\n"
                    "Run python seed.py and python scripts/import_explore.py first.",
                    file=sys.stderr,
                )
                return 1

        print(
            f"Importing {len(stocks_to_process)} symbol(s) "
            f"with period={args.period!r}  dry_run={args.dry_run}"
        )

        results = []
        for stock in stocks_to_process:
            result = import_symbol(db, stock, period=args.period, dry_run=args.dry_run)
            _print_symbol_report(result)
            results.append(result)

        _print_totals(results)

        failed = sum(1 for r in results if r["failed_reason"])
        return 1 if failed == len(results) else 0

    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
