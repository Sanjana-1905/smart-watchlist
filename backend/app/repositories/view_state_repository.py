import uuid
from sqlalchemy.orm import Session
from datetime import datetime
from app.models import UserViewState

def _to_uuid(val):
    if isinstance(val, str):
        try:
            return uuid.UUID(val)
        except ValueError:
            return val
    return val

def get_for_user_stock(db: Session, user_id, stock_id):
    return db.get(UserViewState, {"user_id": _to_uuid(user_id), "stock_id": _to_uuid(stock_id)})

def upsert(db: Session, user_id, stock_id, price, viewed_at: datetime):
    u_id = _to_uuid(user_id)
    s_id = _to_uuid(stock_id)
    existing = get_for_user_stock(db, u_id, s_id)
    if existing:
        existing.last_viewed_at = viewed_at
        existing.last_viewed_price = price
    else:
        existing = UserViewState(
            user_id=u_id, stock_id=s_id,
            last_viewed_at=viewed_at, last_viewed_price=price,
        )
        db.add(existing)
    db.commit()
    return existing

def delete_for_user_stock(db: Session, user_id, stock_id):
    db.query(UserViewState).filter(
        UserViewState.user_id == _to_uuid(user_id),
        UserViewState.stock_id == _to_uuid(stock_id),
    ).delete()
    db.commit()
