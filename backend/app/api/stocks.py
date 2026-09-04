from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

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

@router.get("/{symbol}", response_model=StockOut)
def get_stock(symbol: str, db: Session = Depends(get_db)):
    return _get_stock_or_404(symbol, db)

@router.get("/{symbol}/history", response_model=list[PriceSnapshotOut])
def get_stock_history(symbol: str, db: Session = Depends(get_db)):
    stock = _get_stock_or_404(symbol, db)
    return stock_repository.get_history(db, stock.id)
