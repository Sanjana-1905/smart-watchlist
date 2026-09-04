import yfinance as yf
from datetime import datetime, timezone
from app.providers.base import MarketDataProvider, Quote

def _to_nse_symbol(symbol: str) -> str:
    return f"{symbol}.NS"

class YFinanceProvider(MarketDataProvider):
    def get_quote(self, symbol: str) -> Quote | None:
        try:
            ticker = yf.Ticker(_to_nse_symbol(symbol))
            hist = ticker.history(period="1d")
            if hist.empty:
                return None
            row = hist.iloc[-1]
            return Quote(
                symbol=symbol,
                timestamp=datetime.now(timezone.utc),
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=int(row["Volume"]),
                source="yfinance",
            )
        except Exception:
            # Any failure (network, parsing, rate limit) -> None.
            # Caller (circuit breaker / market_service) decides fallback behavior.
            return None

    def get_quotes(self, symbols: list[str]) -> dict[str, Quote | None]:
        return {s: self.get_quote(s) for s in symbols}
