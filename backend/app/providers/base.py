from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Quote:
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    source: str

class MarketDataProvider(ABC):
    @abstractmethod
    def get_quote(self, symbol: str) -> Quote | None:
        """Return the latest quote for a symbol, or None if unavailable."""
        ...

    @abstractmethod
    def get_quotes(self, symbols: list[str]) -> dict[str, Quote | None]:
        """Batch fetch. Default impl calls get_quote per symbol; override for efficiency."""
        ...
