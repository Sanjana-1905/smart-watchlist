import random
from datetime import datetime, timezone
from app.providers.base import MarketDataProvider, Quote

class MockMarketDataProvider(MarketDataProvider):
    """
    Deterministic, network-free provider. Walks each symbol's price by a small
    random delta per call, seeded per-symbol so repeated runs are reproducible
    within a process, while still producing visible movement over time.
    """

    def __init__(self, base_prices: dict[str, float] | None = None):
        # base_prices: symbol -> last known close, used as the starting point.
        self._base_prices = dict(base_prices or {})
        self._rng = random.Random(42)

    def _walk(self, symbol: str) -> float:
        base = self._base_prices.get(symbol, 1000.0)
        pct_move = self._rng.uniform(-0.008, 0.008)  # +/- 0.8% per tick
        new_price = round(base * (1 + pct_move), 2)
        self._base_prices[symbol] = new_price
        return new_price

    def get_quote(self, symbol: str) -> Quote | None:
        if symbol not in self._base_prices:
            return None
        price = self._walk(symbol)
        volume = self._rng.randint(500_000, 5_000_000)
        now = datetime.now(timezone.utc)
        return Quote(
            symbol=symbol,
            timestamp=now,
            open=price, high=price * 1.002, low=price * 0.998, close=price,
            volume=volume,
            source="mock",
        )

    def get_quotes(self, symbols: list[str]) -> dict[str, Quote | None]:
        return {s: self.get_quote(s) for s in symbols}
