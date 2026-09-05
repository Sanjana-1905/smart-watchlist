"""
app/providers/ticker_map.py — Centralised NSE symbol → Yahoo Finance ticker mapping.

Used by BOTH:
  - scripts/import_market_history.py  (historical ingestion)
  - app/providers/yfinance_provider.py (real-time polling)

Rules
-----
1. Default: append ".NS" to the internal symbol.
2. Explicit overrides in _TICKER_OVERRIDES take priority.
3. None in _TICKER_OVERRIDES means "no Yahoo NSE ticker — skip".
4. _UNSUPPORTED is a convenience alias for the None-valued entries.

Adding a new symbol override
-----------------------------
Add a single line to _TICKER_OVERRIDES.  Both the importer and the real-time
provider pick it up automatically.
"""

# Explicit overrides — only entries that differ from "<SYMBOL>.NS"
_TICKER_OVERRIDES: dict[str, str | None] = {
    # NSE symbol       Yahoo Finance ticker
    # ─────────────────────────────────────────────────────────────────
    # M&M: ampersand is preserved — yfinance handles "M&M.NS" correctly.
    "M&M":        "M&M.NS",

    # BAJAJ-AUTO: Yahoo Finance preserves the hyphen.  BAJAJAUT.NS returns
    # HTTP 404; the default .NS suffix would also work, but keeping the
    # entry here documents the decision explicitly and keeps it tested.
    "BAJAJ-AUTO": "BAJAJ-AUTO.NS",
}


def symbol_to_yahoo_ticker(symbol: str) -> str | None:
    """
    Convert an internal NSE symbol to a Yahoo Finance ticker string.

    Parameters
    ----------
    symbol : str
        Internal NSE symbol (e.g. "ASIANPAINT", "BAJAJ-AUTO", "M&M").

    Returns
    -------
    str | None
        The Yahoo Finance ticker to use, or ``None`` if the symbol is
        known to be unavailable on Yahoo Finance's NSE feed.
    """
    if symbol in _TICKER_OVERRIDES:
        return _TICKER_OVERRIDES[symbol]
    # Default: append .NS
    return f"{symbol}.NS"
