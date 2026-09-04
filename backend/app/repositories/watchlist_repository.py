from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import WatchlistItem, Stock

def list_for_user(db: Session, user_id):
    return db.execute(
        select(WatchlistItem, Stock)
        .join(Stock, WatchlistItem.stock_id == Stock.id)
        .where(WatchlistItem.user_id == user_id)
    ).all()

def get_item(db: Session, user_id, stock_id):
    return db.scalar(
        select(WatchlistItem).where(
            WatchlistItem.user_id == user_id,
            WatchlistItem.stock_id == stock_id,
        )
    )

def add_item(db: Session, item: WatchlistItem):
    db.add(item)
    db.commit()
    return item

def delete_item(db: Session, item: WatchlistItem):
    db.delete(item)
    db.commit()

def list_distinct_watchlisted_stock_ids(db: Session):
    rows = db.execute(select(WatchlistItem.stock_id).distinct()).all()
    return [r[0] for r in rows]
