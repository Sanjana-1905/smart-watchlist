from sqlalchemy.orm import Session
from datetime import datetime
from app.models import UserViewState

def get_for_user_stock(db: Session, user_id, stock_id):
    return db.get(UserViewState, {"user_id": user_id, "stock_id": stock_id})

def upsert(db: Session, user_id, stock_id, price, viewed_at: datetime):
    existing = get_for_user_stock(db, user_id, stock_id)
    if existing:
        existing.last_viewed_at = viewed_at
        existing.last_viewed_price = price
    else:
        existing = UserViewState(
            user_id=user_id, stock_id=stock_id,
            last_viewed_at=viewed_at, last_viewed_price=price,
        )
        db.add(existing)
    db.commit()
    return existing

def delete_for_user_stock(db: Session, user_id, stock_id):
    db.query(UserViewState).filter(
        UserViewState.user_id == user_id,
        UserViewState.stock_id == stock_id,
    ).delete()
    db.commit()
