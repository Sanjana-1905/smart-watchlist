from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Stock, PriceSnapshot

def get_by_symbol(db: Session, symbol: str) -> Stock | None:
    return db.scalar(select(Stock).where(Stock.symbol == symbol.upper()))

def get_all(db: Session) -> list[Stock]:
    return db.scalars(select(Stock)).all()

def get_history(db: Session, stock_id):
    return db.scalars(
        select(PriceSnapshot)
        .where(PriceSnapshot.stock_id == stock_id)
        .order_by(PriceSnapshot.timestamp)
    ).all()

def get_latest_snapshot(db: Session, stock_id):
    return db.scalar(
        select(PriceSnapshot)
        .where(PriceSnapshot.stock_id == stock_id)
        .order_by(PriceSnapshot.timestamp.desc())
    )

def snapshot_exists_at(db: Session, stock_id, timestamp) -> bool:
    return db.scalar(
        select(PriceSnapshot.id).where(
            PriceSnapshot.stock_id == stock_id,
            PriceSnapshot.timestamp == timestamp,
        )
    ) is not None

def create_snapshot(db: Session, snapshot: PriceSnapshot) -> PriceSnapshot:
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot

def get_latest_snapshot_by_symbol(db: Session, symbol: str):
    """Get the latest price snapshot for a symbol (for last-known-good fallback)."""
    from sqlalchemy import select, desc
    stock = get_by_symbol(db, symbol)
    if not stock:
        return None
    return db.scalar(
        select(PriceSnapshot)
        .where(PriceSnapshot.stock_id == stock.id)
        .order_by(desc(PriceSnapshot.timestamp))
    )
