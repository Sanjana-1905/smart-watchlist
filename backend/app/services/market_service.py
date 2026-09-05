import uuid
import redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import PriceSnapshot
from app.repositories import stock_repository, watchlist_repository
from app.providers.mock import MockMarketDataProvider
from app.providers.yfinance_provider import YFinanceProvider
from app.providers.circuit_breaker import CircuitBreaker

_mock_provider_singleton = None

def get_provider(db: Session):
    global _mock_provider_singleton
    if settings.market_provider == "yfinance":
        return YFinanceProvider(), "yfinance"

    if _mock_provider_singleton is None:
        stocks = stock_repository.get_all(db)
        base_prices = {}
        for stock in stocks:
            latest = stock_repository.get_latest_snapshot(db, stock.id)
            if latest:
                base_prices[stock.symbol] = float(latest.close)
        _mock_provider_singleton = MockMarketDataProvider(base_prices)

    return _mock_provider_singleton, "mock"

def poll_once(db: Session, redis_client: redis.Redis) -> dict:
    """
    Fetches quotes for every distinct watchlisted symbol, writes new
    snapshots to PostgreSQL (durable), and caches in Redis (fast).
    
    Returns summary: {fetched, written, skipped_dupe, provider, successful, failed, circuit_open}
    """
    provider, provider_name = get_provider(db)
    breaker = CircuitBreaker(redis_client, provider_name)

    stock_ids = watchlist_repository.list_distinct_watchlisted_stock_ids(db)
    if not stock_ids:
        return {
            "fetched": 0, "written": 0, "skipped_dupe": 0,
            "successful": 0, "failed": 0,
            "provider": provider_name, "circuit_open": False
        }

    stocks = [s for s in stock_repository.get_all(db) if s.id in stock_ids]
    symbols = [s.symbol for s in stocks]
    symbol_to_stock = {s.symbol: s for s in stocks}

    if breaker.is_open():
        return {
            "fetched": 0, "written": 0, "skipped_dupe": 0,
            "successful": 0, "failed": len(symbols),
            "provider": provider_name, "circuit_open": True
        }

    quotes = provider.get_quotes(symbols)

    written = 0
    skipped_dupe = 0
    successful_quotes = 0
    failed_quotes = 0

    for symbol, quote in quotes.items():
        if quote is None:
            failed_quotes += 1
            continue
            
        successful_quotes += 1
        stock = symbol_to_stock[symbol]

        if stock_repository.snapshot_exists_at(db, stock.id, quote.timestamp):
            skipped_dupe += 1
            continue

        # Write to durable PostgreSQL first
        snapshot = PriceSnapshot(
            id=uuid.uuid4(),
            stock_id=stock.id,
            timestamp=quote.timestamp,
            open=quote.open, high=quote.high, low=quote.low, close=quote.close,
            volume=quote.volume,
            source=quote.source,
        )
        stock_repository.create_snapshot(db, snapshot)
        written += 1

        # Cache in Redis for fast access (TTL=5min, just for speed)
        redis_client.set(f"quote:{symbol}", quote.close, ex=300)

    # Circuit breaker logic: only consider success if ALL symbols succeeded
    if successful_quotes == len(symbols):
        breaker.record_success()
    elif successful_quotes == 0:
        breaker.record_failure()
    # else: partial success, log but don't open/close circuit

    return {
        "fetched": len(symbols), "written": written, "skipped_dupe": skipped_dupe,
        "successful": successful_quotes, "failed": failed_quotes,
        "provider": provider_name, "circuit_open": False,
    }
