"""Optional research context. Intentionally independent of all attention calculations."""
import json
import logging
from datetime import date
from pathlib import Path
from typing import Protocol, Literal
from pydantic import BaseModel, HttpUrl

logger = logging.getLogger(__name__)

class ContextItem(BaseModel):
    headline: str
    source: str
    published_date: date
    url: HttpUrl

class ContextOut(BaseModel):
    symbol: str
    status: Literal['AVAILABLE', 'EMPTY', 'UNAVAILABLE']
    provenance: str
    verified_at: date | None = None
    items: list[ContextItem]

class ContextProvider(Protocol):
    def get_context(self, symbol: str) -> ContextOut: ...

class FixtureContextProvider:
    path = Path(__file__).resolve().parents[2] / 'fixtures' / 'related_context.json'

    def get_context(self, symbol: str) -> ContextOut:
        fixture = json.loads(self.path.read_text())
        items = [ContextItem(**row) for row in fixture['items'].get(symbol, [])]
        return ContextOut(symbol=symbol, status='AVAILABLE' if items else 'EMPTY',
            provenance=fixture['provenance'], verified_at=fixture['verified_at'], items=items)

# Future external adapters implement ContextProvider and replace this dependency.
# No network adapter or credentials are required for the default application.
def get_context_provider() -> ContextProvider:
    return FixtureContextProvider()

def read_context(provider: ContextProvider, symbol: str) -> ContextOut:
    try:
        return provider.get_context(symbol)
    except Exception:
        logger.exception('Related context provider failed for %s', symbol)
        return ContextOut(symbol=symbol, status='UNAVAILABLE', provenance='Context provider unavailable', items=[])
