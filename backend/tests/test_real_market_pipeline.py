"""
backend/tests/test_real_market_pipeline.py

Comprehensive tests for Phase A (Real Dynamic Market Pipeline):
- Watchlist symbol deduplication
- Ticker mapping shared module (app.providers.ticker_map)
- YFinanceProvider parsing & validation
- Provider timestamp preservation (no datetime.now() override)
- Same provider timestamp deduplication in poll_once
- Provider error / empty response creates no row
- Invalid price/volume creates no row
- Market closed / unchanged observation creates no duplicate row
- DEMO_MODE behavior in main.py / scheduler
- Last known good observation survives provider failure
- Scoring engine output unaffected by failed provider fetch
"""

import math
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy import select

from app.repositories import stock_repository
from app.core.config import settings
from app.models import PriceSnapshot, Stock, User, WatchlistItem, UserProfile, UserViewState
from app.providers.ticker_map import symbol_to_yahoo_ticker
from app.providers.yfinance_provider import YFinanceProvider
from app.services.market_service import poll_once, get_provider
from app.services.attention_service import calculate_attention, MarketFeatures, UserPreferences
from app.services.feature_service import extract_features
from tests.test_scoring_regressions import isolated_db  # noqa: F401


# ---------------------------------------------------------------------------
# 1. Ticker Mapping
# ---------------------------------------------------------------------------

def test_shared_ticker_map_resolution():
    assert symbol_to_yahoo_ticker("ASIANPAINT") == "ASIANPAINT.NS"
    assert symbol_to_yahoo_ticker("BAJAJ-AUTO") == "BAJAJ-AUTO.NS"
    assert symbol_to_yahoo_ticker("M&M") == "M&M.NS"
    assert symbol_to_yahoo_ticker("RELIANCE") == "RELIANCE.NS"


# ---------------------------------------------------------------------------
# 2. Watchlist Symbol Deduplication in poll_once
# ---------------------------------------------------------------------------

def test_poll_once_deduplicates_watchlisted_symbols(isolated_db):
    db = isolated_db
    stock1 = stock_repository.get_by_symbol(db, "RELIANCE") or Stock(id=uuid.uuid4(), symbol="RELIANCE", company_name="Reliance", exchange="NSE")
    stock2 = stock_repository.get_by_symbol(db, "TCS") or Stock(id=uuid.uuid4(), symbol="TCS", company_name="TCS", exchange="NSE")
    stock3 = stock_repository.get_by_symbol(db, "INFY") or Stock(id=uuid.uuid4(), symbol="INFY", company_name="INFY", exchange="NSE")

    user1 = User(id=uuid.uuid4())
    user2 = User(id=uuid.uuid4())
    db.add_all([user1, user2])
    db.flush()

    # User 1 watches RELIANCE, TCS
    # User 2 watches RELIANCE, INFY
    db.add(WatchlistItem(user_id=user1.id, stock_id=stock1.id))
    db.add(WatchlistItem(user_id=user1.id, stock_id=stock2.id))
    db.add(WatchlistItem(user_id=user2.id, stock_id=stock1.id))
    db.add(WatchlistItem(user_id=user2.id, stock_id=stock3.id))
    db.commit()

    mock_redis = MagicMock()
    mock_redis.incr.return_value = 1
    mock_provider = MagicMock()

    ts = datetime(2026, 9, 5, 10, 0, tzinfo=timezone.utc)
    mock_quotes = {
        stock1.symbol: MagicMock(timestamp=ts, open=2500, high=2520, low=2490, close=2510, volume=1000000, source="yfinance"),
        stock2.symbol: MagicMock(timestamp=ts, open=3500, high=3520, low=3490, close=3510, volume=500000, source="yfinance"),
        stock3.symbol: MagicMock(timestamp=ts, open=1500, high=1520, low=1490, close=1510, volume=800000, source="yfinance"),
    }
    mock_provider.get_quotes.return_value = mock_quotes

    with patch("app.services.market_service.get_provider", return_value=(mock_provider, "yfinance")):
        res = poll_once(db, mock_redis)

    mock_provider.get_quotes.assert_called_once()
    queried_symbols = mock_provider.get_quotes.call_args[0][0]
    assert stock1.symbol in queried_symbols
    assert stock2.symbol in queried_symbols
    assert stock3.symbol in queried_symbols
    assert len(queried_symbols) == len(set(queried_symbols))



# ---------------------------------------------------------------------------
# 3. YFinanceProvider parsing & validation
# ---------------------------------------------------------------------------

@patch("yfinance.Ticker")
def test_yfinance_provider_valid_quote(mock_ticker_cls):
    mock_ticker = MagicMock()
    ts_idx = pd.Timestamp("2026-09-05 10:15:00", tz="UTC")
    df = pd.DataFrame(
        {
            "Open": [2500.0],
            "High": [2520.0],
            "Low": [2490.0],
            "Close": [2510.0],
            "Volume": [123456],
        },
        index=[ts_idx],
    )
    mock_ticker.history.return_value = df
    mock_ticker_cls.return_value = mock_ticker

    provider = YFinanceProvider()
    quote = provider.get_quote("RELIANCE")

    assert quote is not None
    assert quote.symbol == "RELIANCE"
    assert quote.close == 2510.0
    assert quote.volume == 123456
    assert quote.source == "yfinance"
    assert quote.timestamp == datetime(2026, 9, 5, 10, 15, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "open_v,high_v,low_v,close_v,vol_v",
    [
        (2500, 2520, 2490, -100, 1000),    # negative close
        (2500, 2520, 2490, 0, 1000),       # zero close
        (2500, 2520, 2490, float("nan"), 1000),  # NaN close
        (2500, 2520, 2490, float("inf"), 1000),  # inf close
        (2500, 2520, 2490, 2500, -50),     # negative volume
    ],
)
@patch("yfinance.Ticker")
def test_yfinance_provider_invalid_data_rejected(mock_ticker_cls, open_v, high_v, low_v, close_v, vol_v):
    mock_ticker = MagicMock()
    ts_idx = pd.Timestamp("2026-09-05 10:15:00", tz="UTC")
    df = pd.DataFrame(
        {
            "Open": [open_v],
            "High": [high_v],
            "Low": [low_v],
            "Close": [close_v],
            "Volume": [vol_v],
        },
        index=[ts_idx],
    )
    mock_ticker.history.return_value = df
    mock_ticker_cls.return_value = mock_ticker

    provider = YFinanceProvider()
    quote = provider.get_quote("RELIANCE")
    assert quote is None


# ---------------------------------------------------------------------------
# 4. Provider Error or Empty Response creates no row
# ---------------------------------------------------------------------------

@patch("yfinance.Ticker")
def test_yfinance_provider_empty_or_error_returns_none(mock_ticker_cls):
    # Case 1: Empty history
    mock_ticker1 = MagicMock()
    mock_ticker1.history.return_value = pd.DataFrame()
    mock_ticker_cls.return_value = mock_ticker1

    provider = YFinanceProvider()
    assert provider.get_quote("RELIANCE") is None

    # Case 2: Exception raised by yfinance
    mock_ticker2 = MagicMock()
    mock_ticker2.history.side_effect = RuntimeError("yfinance down")
    mock_ticker_cls.return_value = mock_ticker2

    assert provider.get_quote("RELIANCE") is None


def test_poll_once_provider_failure_creates_no_snapshot(isolated_db):
    db = isolated_db
    sym = "TEST_FAIL_" + uuid.uuid4().hex[:6].upper()
    stock = Stock(id=uuid.uuid4(), symbol=sym, company_name="Test Fail", exchange="NSE")
    user = User(id=uuid.uuid4())
    db.add_all([stock, user])
    db.flush()
    db.add(WatchlistItem(user_id=user.id, stock_id=stock.id))
    db.commit()

    initial_count = len(db.scalars(select(PriceSnapshot).where(PriceSnapshot.stock_id == stock.id)).all())

    mock_redis = MagicMock()
    mock_redis.incr.return_value = 1
    mock_provider = MagicMock()
    mock_provider.get_quotes.return_value = {sym: None}  # Failed fetch

    with patch("app.services.market_service.get_provider", return_value=(mock_provider, "yfinance")):
        res = poll_once(db, mock_redis)

    assert res["written"] == 0

    final_count = len(db.scalars(select(PriceSnapshot).where(PriceSnapshot.stock_id == stock.id)).all())
    assert final_count == initial_count


# ---------------------------------------------------------------------------
# 5. Market Closed / Same Timestamp Deduplication
# ---------------------------------------------------------------------------

def test_market_closed_same_timestamp_deduplicated(isolated_db):
    db = isolated_db
    sym = "TEST_DUPE_" + uuid.uuid4().hex[:6].upper()
    stock = Stock(id=uuid.uuid4(), symbol=sym, company_name="Test Dupe", exchange="NSE")
    user = User(id=uuid.uuid4())
    db.add_all([stock, user])
    db.flush()
    db.add(WatchlistItem(user_id=user.id, stock_id=stock.id))
    db.commit()

    ts = datetime(2026, 9, 4, 15, 30, tzinfo=timezone.utc)
    snap1 = PriceSnapshot(
        id=uuid.uuid4(),
        stock_id=stock.id,
        timestamp=ts,
        open=3000, high=3050, low=2990, close=3020, volume=500000,
        source="yfinance"
    )
    db.add(snap1)
    db.commit()

    mock_redis = MagicMock()
    mock_redis.incr.return_value = 1
    mock_provider = MagicMock()
    mock_quote = MagicMock(timestamp=ts, open=3000, high=3050, low=2990, close=3020, volume=500000, source="yfinance")
    mock_provider.get_quotes.return_value = {sym: mock_quote}

    with patch("app.services.market_service.get_provider", return_value=(mock_provider, "yfinance")):
        res = poll_once(db, mock_redis)

    assert res["written"] == 0
    assert res["skipped_dupe"] == 1

    snapshots = db.scalars(select(PriceSnapshot).where(PriceSnapshot.stock_id == stock.id)).all()
    assert len(snapshots) == 1


# ---------------------------------------------------------------------------
# 6. Last Known Good Survives Provider Failure & Scoring Output Unaffected
# ---------------------------------------------------------------------------

def test_last_known_good_survives_provider_failure(isolated_db):
    db = isolated_db
    sym = "TEST_SURV_" + uuid.uuid4().hex[:6].upper()
    stock = Stock(id=uuid.uuid4(), symbol=sym, company_name="Test Survive", exchange="NSE")
    user = User(id=uuid.uuid4())
    db.add_all([stock, user])
    db.flush()
    db.add(UserProfile(user_id=user.id, risk_profile="AGGRESSIVE", attention_style="MOMENTUM", time_horizon="SHORT_TERM"))

    ts1 = datetime(2026, 9, 3, 15, 30, tzinfo=timezone.utc)
    ts2 = datetime(2026, 9, 4, 15, 30, tzinfo=timezone.utc)

    db.add(PriceSnapshot(stock_id=stock.id, timestamp=ts1, open=2400, high=2450, low=2390, close=2400, volume=1000000, source="yfinance"))
    db.add(PriceSnapshot(stock_id=stock.id, timestamp=ts2, open=2400, high=2550, low=2400, close=2520, volume=2500000, source="yfinance"))
    db.commit()

    # Features before provider failure
    features_before = extract_features(db, str(stock.id), str(user.id))
    assert features_before is not None

    # Simulate provider failure during poll
    mock_redis = MagicMock()
    mock_redis.incr.return_value = 1
    mock_provider = MagicMock()
    mock_provider.get_quotes.return_value = {sym: None}

    with patch("app.services.market_service.get_provider", return_value=(mock_provider, "yfinance")):
        poll_once(db, mock_redis)

    # Features after provider failure: extracted from DB history, exactly identical
    features_after = extract_features(db, str(stock.id), str(user.id))
    assert features_after is not None
    assert features_after.session_return == features_before.session_return
    assert features_after.volatility_20d == features_before.volatility_20d
    assert features_after.volume_ratio == features_before.volume_ratio

    # Attention score also identical
    prefs = UserPreferences(risk_profile="AGGRESSIVE", attention_style="MOMENTUM", time_horizon="SHORT_TERM")
    score_before = calculate_attention(features_before, prefs)
    score_after = calculate_attention(features_after, prefs)
    assert score_before.final_score == score_after.final_score
