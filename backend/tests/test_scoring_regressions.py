"""Cross-user API and demo regressions, rolled back after every test."""
import json
import uuid
from dataclasses import replace
from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.database import engine, get_db
from app.core.security import create_access_token
from app.main import app
from app.models import PriceSnapshot, Stock, User, UserProfile, UserViewState, WatchlistItem
from app.services.attention_service import (
    MarketFeatures, UserPreferences, calculate_attention, calculate_objective_score,
)
from app.services.feature_service import extract_features
from scripts import demo
from seed import FIXTURE_PATH, IST


@pytest.fixture
def isolated_db(monkeypatch):
    # Demo helpers commit internally. Savepoints keep those commits inside an
    # outer transaction so these tests never reset the real demo accounts.
    connection = engine.connect()
    transaction = connection.begin()

    def session_factory():
        return Session(bind=connection, join_transaction_mode="create_savepoint")

    def override_db():
        with session_factory() as session:
            yield session

    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(demo, "SessionLocal", session_factory)
    try:
        with session_factory() as session:
            yield session
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        transaction.rollback()
        connection.close()


@pytest.mark.parametrize("since_view", [None, 0, .005, -.03, .05, .20])
def test_objective_ignores_all_since_view_states(since_view):
    market = MarketFeatures(.04, .02, 2, None, True)
    baseline_score, baseline_reasons = calculate_objective_score(market)
    features = replace(market, since_view_return=since_view)
    score, reasons = calculate_objective_score(features)
    assert score == baseline_score
    assert reasons == baseline_reasons
    result = calculate_attention(features, UserPreferences("BALANCED", "BALANCED", "LONG_TERM"))
    since_view_points = min(abs(since_view or 0) / .05, 1) * 20
    long_term_profile_points = min(abs(since_view or 0) / .05, 1) * 5

    expected_personal_relevance = round(
        since_view_points + long_term_profile_points,
        1,
    )

    assert result.preference_fit == pytest.approx(
        expected_personal_relevance
    )
    assert any(r.type == "SINCE_VIEW" for r in result.reasons) == (abs(since_view or 0) >= .01)


def test_different_users_baselines_and_profiles_share_objective(client, isolated_db):
    db = isolated_db
    stock = Stock(id=uuid.uuid4(), symbol=f"TEST{uuid.uuid4().hex[:8].upper()}", company_name="Test", exchange="NSE")
    users = [User(id=uuid.uuid4()), User(id=uuid.uuid4())]
    db.add_all([stock, *users])
    db.flush()
    for user, baseline, profile in zip(users, [100, 102], [
        ("AGGRESSIVE", "MOMENTUM", "SHORT_TERM"),
        ("CONSERVATIVE", "STABILITY", "LONG_TERM"),
    ]):
        db.add(UserProfile(user_id=user.id, risk_profile=profile[0], attention_style=profile[1], time_horizon=profile[2], version=1, onboarding_completed=True))
        db.add(WatchlistItem(user_id=user.id, stock_id=stock.id))
        db.add(UserViewState(user_id=user.id, stock_id=stock.id, last_viewed_price=baseline, last_viewed_at=datetime(2026, 9, 3, tzinfo=timezone.utc)))
    # Repeated polls on the historical session must NOT inflate its volume.
    for day, hour, close, volume in [(3, 5, 99, 400), (3, 10, 100, 1000), (4, 5, 102, 500), (4, 10, 104, 2000)]:
        db.add(PriceSnapshot(stock_id=stock.id, timestamp=datetime(2026, 9, day, hour, tzinfo=timezone.utc), open=close, high=close, low=close, close=close, volume=volume, source="mock"))
    db.commit()
    headers = [{"Authorization": "Bearer " + create_access_token(user.id)} for user in users]

    def changes(header):
        response = client.get("/watchlist/changes", headers=header)
        assert response.status_code == 200, response.text
        return {key: value for key, value in response.json()["items"][0].items() if key != "freshness"}

    a, b = map(changes, headers)
    assert a["current_price"] == b["current_price"] == 104
    assert a["session_change_pct"] == b["session_change_pct"] == 4
    assert a["since_last_view_pct"] == 4
    assert b["since_last_view_pct"] == 1.96
    assert a["objective_score"] == b["objective_score"]
    assert a["preference_fit"] == 31
    assert b["preference_fit"] == 9.8
    assert a["attention_score"] != b["attention_score"]
    for user in users:
        features = extract_features(db, stock.id, user.id)
        assert features.volume_ratio == 2
        assert features.session_return == pytest.approx(.04)
    assert any(r["type"] == "SINCE_VIEW" for r in a["reasons"])
    assert any(r["type"] == "SINCE_VIEW" for r in b["reasons"])

    response = client.post("/watchlist/viewed", headers=headers[0], json={"symbol": stock.symbol})
    assert response.status_code == 204
    caught_up = changes(headers[0])
    assert caught_up["since_last_view_pct"] == 0
    assert caught_up["objective_score"] == a["objective_score"]
    assert changes(headers[1]) == b


def test_demo_real_history_replay_reset_and_advance(client, isolated_db):
    db = isolated_db
    # Populate fixture history if not present
    fixture = json.loads(FIXTURE_PATH.read_text())
    stocks = {s.symbol: s for s in db.scalars(select(Stock)).all()}
    for symbol in ["RELIANCE", "ASIANPAINT", "HDFCBANK", "TCS", "BEL", "TATASTEEL", "BAJAJ-AUTO", "M&M"]:
        if symbol in stocks:
            stock = stocks[symbol]
            existing = db.scalars(select(PriceSnapshot).where(PriceSnapshot.stock_id == stock.id)).all()
            if not existing and symbol in fixture:
                for row in fixture[symbol]["history"]:
                    db.add(PriceSnapshot(stock_id=stock.id, timestamp=datetime.strptime(row["date"], "%Y-%m-%d").replace(hour=15, minute=30, tzinfo=IST), open=row["open"], high=row["high"], low=row["low"], close=row["close"], volume=row["volume"], source="yfinance_fixture"))
    db.commit()

    def snapshot():
        result = {}
        for uid in demo.DEMO_USER_IDS:
            response = client.get("/watchlist/changes", headers={"Authorization": "Bearer " + create_access_token(uuid.UUID(uid))})
            assert response.status_code == 200, response.text
            result[uid] = {item["symbol"]: {key: value for key, value in item.items() if key != "freshness"} for item in response.json()["items"]}
        return result

    # 1. Reset: both users set to baseline Session A
    demo.cmd_reset()
    reset_state = snapshot()
    demo.cmd_reset()
    assert snapshot() == reset_state, "Reset must be idempotent"

    # Verify both users share the EXACT same objective score & current price
    p_uid, s_uid = demo.DEMO_USER_IDS[0], demo.DEMO_USER_IDS[1]
    for sym in reset_state[p_uid]:
        if sym in reset_state[s_uid]:
            item_p = reset_state[p_uid][sym]
            item_s = reset_state[s_uid][sym]
            assert item_p["current_price"] == item_s["current_price"]
            assert item_p["objective_score"] == item_s["objective_score"]
            assert item_p["session_change_pct"] == item_s["session_change_pct"]

    # 2. Advance: user baselines advance to Session B (caught up)
    demo.cmd_advance()
    advanced_state = snapshot()
    demo.cmd_advance()
    assert snapshot() == advanced_state, "Advance must be idempotent"

    # Verify since_last_view_pct is reset/caught up after advancing
    for sym, item in advanced_state[p_uid].items():
        assert item["since_last_view_pct"] in (0, 0.0, None) or item["since_last_view_pct"] == pytest.approx(0)
