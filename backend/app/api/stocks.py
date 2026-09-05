from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine

from app.core.database import get_db
from app.core.errors import AppError
from app.repositories import stock_repository
from app.schemas.stock import StockOut, PriceSnapshotOut

router = APIRouter(prefix="/stocks", tags=["stocks"])

def _get_stock_or_404(symbol: str, db: Session):
    stock = stock_repository.get_by_symbol(db, symbol)
    if not stock:
        raise AppError(404, "STOCK_NOT_FOUND", f"No stock with symbol {symbol}")
    return stock

@router.get("", response_model=list[StockOut])
def list_stocks(db: Session = Depends(get_db)):
    """Full catalog — public, since this is just the market universe, not user data."""
    return stock_repository.get_all(db)

@router.get("/{symbol}", response_model=StockOut)
def get_stock(symbol: str, db: Session = Depends(get_db)):
    return _get_stock_or_404(symbol, db)

@router.get("/{symbol}/history", response_model=list[PriceSnapshotOut])
def get_stock_history(symbol: str, db: Session = Depends(get_db)):
    stock = _get_stock_or_404(symbol, db)
    return stock_repository.get_history(db, stock.id)

# Additive authenticated projection. Reading it never marks a stock as viewed.
from uuid import UUID
from app.core.current_user import get_current_user_id
from app.services.analytics_service import build_analytics
from app.schemas.analytics import AnalyticsOut

@router.get("/{symbol}/analytics", response_model=AnalyticsOut)
def get_stock_analytics(symbol: str, db: Session = Depends(get_db), user_id: UUID = Depends(get_current_user_id)):
    # One MVCC snapshot for all repository/engine reads, even if a poll arrives
    # midway through the response. Transaction-bound test sessions retain their
    # caller's transaction (and roll back all fixture state).
    if isinstance(db.get_bind(), Engine):
        db.connection(execution_options={"isolation_level": "REPEATABLE READ", "postgresql_readonly": True})
    return build_analytics(db, _get_stock_or_404(symbol.upper(), db), user_id)

from app.services.context_service import ContextProvider, ContextOut, get_context_provider, read_context

@router.get("/{symbol}/context", response_model=ContextOut)
def get_stock_context(symbol: str, db: Session = Depends(get_db),
                      user_id: UUID = Depends(get_current_user_id),
                      provider: ContextProvider = Depends(get_context_provider)):
    stock = _get_stock_or_404(symbol.upper(), db)
    return read_context(provider, stock.symbol)
