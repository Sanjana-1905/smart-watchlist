import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.core.errors import AppError
from app.core.current_user import get_current_user_id
from app.models import WatchlistItem
from app.repositories import stock_repository, watchlist_repository, view_state_repository
from app.schemas.watchlist import WatchlistItemOut, AddWatchlistItemIn, ViewedIn

router = APIRouter(prefix="/watchlist", tags=["watchlist"])

@router.get("", response_model=list[WatchlistItemOut])
def list_watchlist(db: Session = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    rows = watchlist_repository.list_for_user(db, user_id)
    return [
        WatchlistItemOut(symbol=stock.symbol, company_name=stock.company_name, added_at=item.added_at)
        for item, stock in rows
    ]

@router.post("/items", response_model=WatchlistItemOut, status_code=201)
def add_watchlist_item(
    payload: AddWatchlistItemIn,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    symbol = payload.symbol.upper()
    stock = stock_repository.get_by_symbol(db, symbol)
    if not stock:
        raise AppError(404, "STOCK_NOT_FOUND", f"No stock with symbol {symbol}")

    item = WatchlistItem(
        id=uuid.uuid4(), user_id=user_id, stock_id=stock.id,
        added_at=datetime.now(timezone.utc), version=1,
    )
    try:
        watchlist_repository.add_item(db, item)
    except IntegrityError:
        db.rollback()
        raise AppError(409, "WATCHLIST_DUPLICATE", f"{symbol} is already in your watchlist")

    return WatchlistItemOut(symbol=stock.symbol, company_name=stock.company_name, added_at=item.added_at)

@router.delete("/items/{symbol}", status_code=204)
def remove_watchlist_item(
    symbol: str,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    symbol = symbol.upper()
    stock = stock_repository.get_by_symbol(db, symbol)
    if not stock:
        raise AppError(404, "STOCK_NOT_FOUND", f"No stock with symbol {symbol}")

    item = watchlist_repository.get_item(db, user_id, stock.id)
    if not item:
        raise AppError(404, "WATCHLIST_ITEM_NOT_FOUND", f"{symbol} is not in your watchlist")

    view_state_repository.delete_for_user_stock(db, user_id, stock.id)
    watchlist_repository.delete_item(db, item)
    return None

@router.post("/viewed", status_code=204)
def mark_viewed(
    payload: ViewedIn,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    symbol = payload.symbol.upper()
    stock = stock_repository.get_by_symbol(db, symbol)
    if not stock:
        raise AppError(404, "STOCK_NOT_FOUND", f"No stock with symbol {symbol}")

    latest = stock_repository.get_latest_snapshot(db, stock.id)
    if not latest:
        raise AppError(409, "MARKET_DATA_UNAVAILABLE", f"No price data available for {symbol}")

    view_state_repository.upsert(db, user_id, stock.id, latest.close, datetime.now(timezone.utc))
    return None
