import math
from datetime import datetime, timezone
import yfinance as yf
from app.providers.base import MarketDataProvider, Quote
from app.providers.ticker_map import symbol_to_yahoo_ticker

class YFinanceProvider(MarketDataProvider):
    def get_quote(self, symbol: str) -> Quote | None:
        try:
            ticker_str = symbol_to_yahoo_ticker(symbol)
            if not ticker_str:
                return None

            ticker = yf.Ticker(ticker_str)
            hist = ticker.history(period="1d")
            if hist.empty:
                return None

            row = hist.iloc[-1]

            # Extract actual provider timestamp from index
            idx_ts = hist.index[-1]
            if hasattr(idx_ts, "to_pydatetime"):
                dt = idx_ts.to_pydatetime()
            else:
                dt = idx_ts
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)

            open_p = float(row["Open"])
            high_p = float(row["High"])
            low_p = float(row["Low"])
            close_p = float(row["Close"])
            volume_v = int(row["Volume"])

            # Validation: no NaN, infinity, non-positive close, negative volume
            for val in (open_p, high_p, low_p, close_p):
                if not math.isfinite(val) or val <= 0:
                    return None
            if not math.isfinite(volume_v) or volume_v < 0:
                return None

            return Quote(
                symbol=symbol,
                timestamp=dt,
                open=open_p,
                high=high_p,
                low=low_p,
                close=close_p,
                volume=volume_v,
                source="yfinance",
            )
        except Exception:
            return None

    def get_quotes(self, symbols: list[str]) -> dict[str, Quote | None]:
        return {s: self.get_quote(s) for s in symbols}
