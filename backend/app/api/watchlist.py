import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, Response
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.core.errors import AppError
from app.core.current_user import get_current_user_id
from app.core.market_clock import get_market_status
from app.core.freshness import evaluate_freshness
from app.core.redis_client import get_redis
from app.core.idempotency import get_cached_response, store_response
from app.models import WatchlistItem, UserProfile
from app.repositories import stock_repository, watchlist_repository, view_state_repository, profile_repository
from app.services.feature_service import extract_features
from app.services.attention_service import (
    calculate_attention,
    UserPreferences,
)
from app.schemas.watchlist import WatchlistItemOut, AddWatchlistItemIn, ViewedIn
from app.schemas.watchlist_changes import (
    WatchlistChangesOut,
    WatchlistChangeItemOut,
    ReasonOut,
    FreshnessOut,
)

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
    response: Response,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
    redis_client=Depends(get_redis),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    cached = get_cached_response(redis_client, user_id, idempotency_key)
    if cached is not None:
        status_code, body = cached
        response.status_code = status_code
        return body

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

    result = WatchlistItemOut(symbol=stock.symbol, company_name=stock.company_name, added_at=item.added_at)
    store_response(redis_client, user_id, idempotency_key, 201, jsonable_encoder(result))
    return result


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
    response: Response,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
    redis_client=Depends(get_redis),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    cached = get_cached_response(redis_client, user_id, idempotency_key)
    if cached is not None:
        status_code, _ = cached
        response.status_code = status_code
        return None

    symbol = payload.symbol.upper()
    stock = stock_repository.get_by_symbol(db, symbol)
    if not stock:
        raise AppError(404, "STOCK_NOT_FOUND", f"No stock with symbol {symbol}")

    latest = stock_repository.get_latest_snapshot(db, stock.id)
    if not latest:
        raise AppError(409, "MARKET_DATA_UNAVAILABLE", f"No price data available for {symbol}")

    view_state_repository.upsert(db, user_id, stock.id, latest.close, datetime.now(timezone.utc))
    store_response(redis_client, user_id, idempotency_key, 204, None)
    return None


@router.get("/changes", response_model=WatchlistChangesOut)
def get_watchlist_changes(
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    profile = profile_repository.get_for_user(db, user_id)
    if not profile:
        raise AppError(404, "PROFILE_NOT_FOUND", "No profile found for user")

    preferences = UserPreferences(
        risk_profile=profile.risk_profile,
        attention_style=profile.attention_style,
        time_horizon=profile.time_horizon,
    )

    rows = watchlist_repository.list_for_user(db, user_id)

    if not rows:
        return WatchlistChangesOut(
            generated_at=datetime.now(timezone.utc),
            market_status=get_market_status(),
            items=[],
        )

    items = []
    now = datetime.now(timezone.utc)

    for watchlist_item, stock in rows:
        features = extract_features(db, stock.id, user_id)
        if features is None:
            continue

        result = calculate_attention(features, preferences)

        latest_snap = stock_repository.get_latest_snapshot(db, stock.id)
        freshness = evaluate_freshness(
            latest_snap.timestamp if latest_snap else None,
            latest_snap.source if latest_snap else "unknown",
            now,
        )

        item = WatchlistChangeItemOut(
            symbol=stock.symbol,
            company_name=stock.company_name,
            current_price=float(latest_snap.close) if latest_snap else 0,
            session_change_pct=round(features.session_return * 100, 2),
            since_last_view_pct=round(features.since_view_return * 100, 2) if features.since_view_return is not None else None,
            objective_score=result.objective_score,
            preference_fit=result.preference_fit,
            attention_score=result.final_score,
            attention_level=result.level,
            reasons=[
                ReasonOut(type=r.type, value=r.value, message=r.message)
                for r in result.reasons
            ],
            freshness=FreshnessOut(
                status=freshness.status,
                observed_at=freshness.observed_at or now,
                source=freshness.source,
                age_minutes=freshness.age_minutes,
            ),
        )
        items.append(item)

    items.sort(key=lambda x: x.attention_score, reverse=True)

    return WatchlistChangesOut(
        generated_at=now,
        market_status=get_market_status(),
        items=items,
    )
