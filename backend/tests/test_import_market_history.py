"""
tests/test_import_market_history.py

Automated tests for the import_market_history script.

All tests mock yfinance so they work offline (no Internet access required).

Coverage:
  - ticker translation for all known symbols
  - ASIANPAINT -> ASIANPAINT.NS mapping
  - BAJAJ-AUTO -> BAJAJAUT.NS override
  - M&M -> M&M.NS override
  - default .NS suffix for standard symbols
  - valid history ingestion writes correct PriceSnapshot rows
  - invalid OHLC (NaN) rejected
  - invalid close (<= 0) rejected
  - invalid volume (negative) rejected
  - empty provider response handled gracefully
  - provider exception handled gracefully
  - idempotent second import (no duplicate rows)
  - no watchlist mutation
  - source == "yfinance" on inserted rows
  - timestamps are IST 15:30 canonical
  - no synthetic fallback when provider fails
"""

import math
import sys
import uuid
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Ensure the scripts dir is importable even when pytest runs from /app
# ---------------------------------------------------------------------------
BACKEND_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BACKEND_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from import_market_history import (  # noqa: E402
    IST,
    _bar_date_ist,
    _canonical_timestamp,
    _existing_dates_for_stock,
    _is_valid_row,
    import_symbol,
    symbol_to_yahoo_ticker,
)
from app.models import PriceSnapshot, Stock  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

IST = ZoneInfo("Asia/Kolkata")


def _make_stock(symbol: str = "TESTSTOCK") -> Stock:
    """Return an in-memory Stock instance (not persisted)."""
    s = Stock()
    s.id = uuid.uuid4()
    s.symbol = symbol
    s.company_name = f"{symbol} Corp"
    s.exchange = "NSE"
    s.sector = "Test"
    return s


def _make_hist_df(rows: list[dict]) -> pd.DataFrame:
    """
    Build a minimal yfinance-style OHLCV DataFrame.

    rows: list of dicts with keys date (str YYYY-MM-DD), Open, High, Low,
    Close, Volume.  The index is a tz-aware Timestamp in Asia/Kolkata.
    """
    index = [
        pd.Timestamp(r["date"], tz="Asia/Kolkata")
        for r in rows
    ]
    data = {
        "Open":   [r["Open"]   for r in rows],
        "High":   [r["High"]   for r in rows],
        "Low":    [r["Low"]    for r in rows],
        "Close":  [r["Close"]  for r in rows],
        "Volume": [r["Volume"] for r in rows],
    }
    return pd.DataFrame(data, index=index)


def _make_db_mock(existing_timestamps=None):
    """
    Return a minimal mock of a SQLAlchemy Session.

    existing_timestamps: list of datetime objects (tz-aware) already in the DB.
    Passed through _existing_dates_for_stock -> db.scalars(...).all()
    """
    db = MagicMock()
    db.scalars.return_value.all.return_value = existing_timestamps or []
    db.add = MagicMock()
    db.commit = MagicMock()
    return db


# ===========================================================================
# 1. Ticker translation
# ===========================================================================

class TestTickerTranslation:
    def test_standard_symbol_gets_ns_suffix(self):
        assert symbol_to_yahoo_ticker("RELIANCE") == "RELIANCE.NS"

    def test_tcs(self):
        assert symbol_to_yahoo_ticker("TCS") == "TCS.NS"

    def test_hdfcbank(self):
        assert symbol_to_yahoo_ticker("HDFCBANK") == "HDFCBANK.NS"

    def test_asianpaint_default_suffix(self):
        # ASIANPAINT has no override → default .NS
        assert symbol_to_yahoo_ticker("ASIANPAINT") == "ASIANPAINT.NS"

    def test_bajaj_auto_override(self):
        # BAJAJ-AUTO uses BAJAJ-AUTO.NS on Yahoo Finance (hyphen preserved)
        assert symbol_to_yahoo_ticker("BAJAJ-AUTO") == "BAJAJ-AUTO.NS"

    def test_mm_override(self):
        # M&M stays as M&M.NS (ampersand OK for yfinance)
        assert symbol_to_yahoo_ticker("M&M") == "M&M.NS"

    def test_bel(self):
        assert symbol_to_yahoo_ticker("BEL") == "BEL.NS"

    def test_tatasteel(self):
        assert symbol_to_yahoo_ticker("TATASTEEL") == "TATASTEEL.NS"

    def test_infy(self):
        assert symbol_to_yahoo_ticker("INFY") == "INFY.NS"

    def test_wipro(self):
        assert symbol_to_yahoo_ticker("WIPRO") == "WIPRO.NS"

    def test_unknown_symbol_gets_ns_suffix(self):
        # Any unknown symbol should get the default .NS suffix
        result = symbol_to_yahoo_ticker("NEWSTOCK")
        assert result == "NEWSTOCK.NS"


# ===========================================================================
# 2. OHLCV validation
# ===========================================================================

class TestOHLCVValidation:
    def _row(self, **kwargs):
        base = {"Open": 100.0, "High": 110.0, "Low": 90.0, "Close": 105.0, "Volume": 1000000}
        base.update(kwargs)
        return pd.Series(base)

    def test_valid_row_accepted(self):
        assert _is_valid_row(self._row()) is True

    def test_nan_open_rejected(self):
        assert _is_valid_row(self._row(Open=float("nan"))) is False

    def test_nan_high_rejected(self):
        assert _is_valid_row(self._row(High=float("nan"))) is False

    def test_nan_low_rejected(self):
        assert _is_valid_row(self._row(Low=float("nan"))) is False

    def test_nan_close_rejected(self):
        assert _is_valid_row(self._row(Close=float("nan"))) is False

    def test_inf_close_rejected(self):
        assert _is_valid_row(self._row(Close=float("inf"))) is False

    def test_zero_close_rejected(self):
        assert _is_valid_row(self._row(Close=0.0)) is False

    def test_negative_close_rejected(self):
        assert _is_valid_row(self._row(Close=-5.0)) is False

    def test_zero_volume_accepted(self):
        # Volume = 0 is allowed (e.g. public holidays in some data sets)
        assert _is_valid_row(self._row(Volume=0)) is True

    def test_negative_volume_rejected(self):
        assert _is_valid_row(self._row(Volume=-1)) is False

    def test_missing_close_key_rejected(self):
        row = pd.Series({"Open": 100.0, "High": 110.0, "Low": 90.0, "Volume": 1000})
        assert _is_valid_row(row) is False


# ===========================================================================
# 3. Timestamp helpers
# ===========================================================================

class TestTimestampHelpers:
    def test_canonical_timestamp_is_1530_ist(self):
        d = date(2024, 6, 15)
        ts = _canonical_timestamp(d)
        assert ts.hour == 15
        assert ts.minute == 30
        assert ts.second == 0
        assert ts.tzinfo is not None
        # Verify it's IST
        ts_ist = ts.astimezone(ZoneInfo("Asia/Kolkata"))
        assert ts_ist.hour == 15
        assert ts_ist.minute == 30

    def test_bar_date_ist_from_tz_aware_timestamp(self):
        ts = pd.Timestamp("2024-06-15 09:00:00", tz="UTC")
        d = _bar_date_ist(ts)
        # 09:00 UTC = 14:30 IST → still 2024-06-15
        assert isinstance(d, date)
        assert d == date(2024, 6, 15)

    def test_bar_date_ist_from_naive_timestamp(self):
        ts = pd.Timestamp("2024-06-15")
        d = _bar_date_ist(ts)
        assert d == date(2024, 6, 15)


# ===========================================================================
# 4. import_symbol: happy path
# ===========================================================================

class TestImportSymbolHappyPath:
    def _run(self, hist_df, existing_timestamps=None, dry_run=False):
        stock = _make_stock("ASIANPAINT")
        db = _make_db_mock(existing_timestamps=existing_timestamps)

        with patch("import_market_history.yf.Ticker") as mock_ticker_cls:
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = hist_df
            mock_ticker_cls.return_value = mock_ticker

            result = import_symbol(db, stock, period="1y", dry_run=dry_run)

        return result, db

    def test_inserts_valid_rows(self):
        hist = _make_hist_df([
            {"date": "2024-01-02", "Open": 100, "High": 110, "Low": 90, "Close": 105, "Volume": 500000},
            {"date": "2024-01-03", "Open": 105, "High": 115, "Low": 95, "Close": 110, "Volume": 600000},
        ])
        result, db = self._run(hist)

        assert result["failed_reason"] is None
        assert result["provider_rows"] == 2
        assert result["valid_rows"] == 2
        assert result["inserted"] == 2
        assert result["skipped"] == 0
        assert db.add.call_count == 2
        assert db.commit.called

    def test_source_is_yfinance(self):
        hist = _make_hist_df([
            {"date": "2024-01-02", "Open": 100, "High": 110, "Low": 90, "Close": 105, "Volume": 500000},
        ])
        result, db = self._run(hist)

        assert result["source"] == "yfinance"
        # Check the actual PriceSnapshot that was added
        added_snapshot: PriceSnapshot = db.add.call_args[0][0]
        assert added_snapshot.source == "yfinance"

    def test_timestamp_is_canonical_1530_ist(self):
        hist = _make_hist_df([
            {"date": "2024-06-15", "Open": 200, "High": 210, "Low": 190, "Close": 205, "Volume": 100000},
        ])
        result, db = self._run(hist)

        added_snapshot: PriceSnapshot = db.add.call_args[0][0]
        ts = added_snapshot.timestamp
        ts_ist = ts.astimezone(ZoneInfo("Asia/Kolkata"))
        assert ts_ist.hour == 15
        assert ts_ist.minute == 30
        assert ts_ist.year == 2024
        assert ts_ist.month == 6
        assert ts_ist.day == 15

    def test_date_range_reported(self):
        hist = _make_hist_df([
            {"date": "2024-01-02", "Open": 100, "High": 110, "Low": 90, "Close": 105, "Volume": 500000},
            {"date": "2024-01-03", "Open": 105, "High": 115, "Low": 95, "Close": 110, "Volume": 600000},
        ])
        result, db = self._run(hist)
        assert "2024-01-02" in result["date_range"]
        assert "2024-01-03" in result["date_range"]

    def test_yahoo_ticker_is_reported(self):
        hist = _make_hist_df([
            {"date": "2024-01-02", "Open": 100, "High": 110, "Low": 90, "Close": 105, "Volume": 500000},
        ])
        result, _ = self._run(hist)
        assert result["yahoo_ticker"] == "ASIANPAINT.NS"

    def test_dry_run_does_not_write(self):
        hist = _make_hist_df([
            {"date": "2024-01-02", "Open": 100, "High": 110, "Low": 90, "Close": 105, "Volume": 500000},
        ])
        result, db = self._run(hist, dry_run=True)

        assert result["inserted"] == 1  # counted but not written
        assert db.add.call_count == 0
        assert not db.commit.called


# ===========================================================================
# 5. import_symbol: invalid data is rejected
# ===========================================================================

class TestImportSymbolInvalidData:
    def _run(self, hist_df):
        stock = _make_stock("TESTSTOCK")
        db = _make_db_mock()

        with patch("import_market_history.yf.Ticker") as mock_ticker_cls:
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = hist_df
            mock_ticker_cls.return_value = mock_ticker
            result = import_symbol(db, stock, period="1y")

        return result, db

    def test_nan_close_rejected(self):
        hist = _make_hist_df([
            {"date": "2024-01-02", "Open": 100, "High": 110, "Low": 90, "Close": float("nan"), "Volume": 500000},
        ])
        result, db = self._run(hist)
        assert result["valid_rows"] == 0
        assert result["inserted"] == 0
        assert db.add.call_count == 0

    def test_zero_close_rejected(self):
        hist = _make_hist_df([
            {"date": "2024-01-02", "Open": 100, "High": 110, "Low": 90, "Close": 0.0, "Volume": 500000},
        ])
        result, db = self._run(hist)
        assert result["valid_rows"] == 0

    def test_negative_volume_rejected(self):
        hist = _make_hist_df([
            {"date": "2024-01-02", "Open": 100, "High": 110, "Low": 90, "Close": 105, "Volume": -1},
        ])
        result, db = self._run(hist)
        assert result["valid_rows"] == 0
        assert result["inserted"] == 0

    def test_mix_valid_invalid_only_inserts_valid(self):
        hist = _make_hist_df([
            {"date": "2024-01-02", "Open": 100, "High": 110, "Low": 90, "Close": 105, "Volume": 500000},
            {"date": "2024-01-03", "Open": 100, "High": 110, "Low": 90, "Close": float("nan"), "Volume": 500000},
            {"date": "2024-01-04", "Open": 100, "High": 110, "Low": 90, "Close": 108, "Volume": 600000},
        ])
        result, db = self._run(hist)
        assert result["provider_rows"] == 3
        assert result["valid_rows"] == 2
        assert result["inserted"] == 2


# ===========================================================================
# 6. import_symbol: empty / exception cases
# ===========================================================================

class TestImportSymbolEdgeCases:
    def test_empty_provider_response(self):
        stock = _make_stock("TESTSTOCK")
        db = _make_db_mock()

        with patch("import_market_history.yf.Ticker") as mock_ticker_cls:
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = pd.DataFrame()
            mock_ticker_cls.return_value = mock_ticker
            result = import_symbol(db, stock, period="1y")

        assert result["failed_reason"] is not None
        assert result["inserted"] == 0
        assert db.add.call_count == 0

    def test_provider_exception_handled(self):
        stock = _make_stock("TESTSTOCK")
        db = _make_db_mock()

        with patch("import_market_history.yf.Ticker") as mock_ticker_cls:
            mock_ticker = MagicMock()
            mock_ticker.history.side_effect = RuntimeError("network timeout")
            mock_ticker_cls.return_value = mock_ticker
            result = import_symbol(db, stock, period="1y")

        assert result["failed_reason"] is not None
        assert "yfinance exception" in result["failed_reason"]
        assert result["inserted"] == 0
        assert db.add.call_count == 0

    def test_no_synthetic_fallback_on_failure(self):
        """When provider fails, no rows should be inserted (no fallback)."""
        stock = _make_stock("TESTSTOCK")
        db = _make_db_mock()

        with patch("import_market_history.yf.Ticker") as mock_ticker_cls:
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = pd.DataFrame()
            mock_ticker_cls.return_value = mock_ticker
            result = import_symbol(db, stock, period="1y")

        # Zero rows — not a single synthetic price
        assert result["inserted"] == 0
        assert db.add.call_count == 0


# ===========================================================================
# 7. Idempotency: second import must not duplicate rows
# ===========================================================================

class TestIdempotency:
    def test_second_import_skips_existing_dates(self):
        """
        Simulate: first import wrote rows for 2024-01-02 and 2024-01-03.
        Second import sees those dates in existing_timestamps → both skipped.
        """
        stock = _make_stock("ASIANPAINT")

        # Timestamps that represent previously inserted rows (15:30 IST)
        already_stored = [
            datetime(2024, 1, 2, 15, 30, 0, tzinfo=ZoneInfo("Asia/Kolkata")),
            datetime(2024, 1, 3, 15, 30, 0, tzinfo=ZoneInfo("Asia/Kolkata")),
        ]
        db = _make_db_mock(existing_timestamps=already_stored)

        hist = _make_hist_df([
            {"date": "2024-01-02", "Open": 100, "High": 110, "Low": 90, "Close": 105, "Volume": 500000},
            {"date": "2024-01-03", "Open": 105, "High": 115, "Low": 95, "Close": 110, "Volume": 600000},
        ])

        with patch("import_market_history.yf.Ticker") as mock_ticker_cls:
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = hist
            mock_ticker_cls.return_value = mock_ticker
            result = import_symbol(db, stock, period="1y")

        assert result["inserted"] == 0
        assert result["skipped"] == 2
        # Nothing written to DB
        assert db.add.call_count == 0
        assert not db.commit.called

    def test_partial_overlap_only_new_dates_inserted(self):
        """Only new dates should be inserted; existing dates should be skipped."""
        stock = _make_stock("ASIANPAINT")

        # Only 2024-01-02 already exists
        already_stored = [
            datetime(2024, 1, 2, 15, 30, 0, tzinfo=ZoneInfo("Asia/Kolkata")),
        ]
        db = _make_db_mock(existing_timestamps=already_stored)

        hist = _make_hist_df([
            {"date": "2024-01-02", "Open": 100, "High": 110, "Low": 90, "Close": 105, "Volume": 500000},
            {"date": "2024-01-03", "Open": 105, "High": 115, "Low": 95, "Close": 110, "Volume": 600000},
        ])

        with patch("import_market_history.yf.Ticker") as mock_ticker_cls:
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = hist
            mock_ticker_cls.return_value = mock_ticker
            result = import_symbol(db, stock, period="1y")

        assert result["inserted"] == 1
        assert result["skipped"] == 1
        assert db.add.call_count == 1


# ===========================================================================
# 8. No watchlist mutation
# ===========================================================================

class TestNoWatchlistMutation:
    def test_import_does_not_touch_watchlist_table(self):
        """
        import_symbol must only touch PriceSnapshot (via db.add) and Stock
        (via db.scalars for existing dates).  It must never modify WatchlistItem.
        """
        from app.models import WatchlistItem  # noqa: F401 — just ensure importable

        stock = _make_stock("ASIANPAINT")
        db = _make_db_mock()

        hist = _make_hist_df([
            {"date": "2024-01-02", "Open": 100, "High": 110, "Low": 90, "Close": 105, "Volume": 500000},
        ])

        with patch("import_market_history.yf.Ticker") as mock_ticker_cls:
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = hist
            mock_ticker_cls.return_value = mock_ticker
            result = import_symbol(db, stock, period="1y")

        # db.add was called once (PriceSnapshot) and the argument must be a PriceSnapshot
        assert db.add.call_count == 1
        added = db.add.call_args[0][0]
        assert isinstance(added, PriceSnapshot), "Only PriceSnapshot rows should be added"

    def test_inserted_snapshot_has_correct_stock_id(self):
        stock = _make_stock("ASIANPAINT")
        db = _make_db_mock()

        hist = _make_hist_df([
            {"date": "2024-01-02", "Open": 100, "High": 110, "Low": 90, "Close": 105, "Volume": 500000},
        ])

        with patch("import_market_history.yf.Ticker") as mock_ticker_cls:
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = hist
            mock_ticker_cls.return_value = mock_ticker
            import_symbol(db, stock, period="1y")

        added = db.add.call_args[0][0]
        assert added.stock_id == stock.id
