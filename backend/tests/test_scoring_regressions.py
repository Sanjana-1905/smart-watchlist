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
    assert result.preference_fit == pytest.approx(round(min(abs(since_view or 0) / .05, 1) * 20, 1))
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
    assert b["preference_fit"] == 7.8
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


def test_demo_volume_and_repeated_reset_advance(client, isolated_db, monkeypatch):
    db = isolated_db

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            instant = datetime(2026, 9, 5, 7, tzinfo=timezone.utc)
            return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)

    monkeypatch.setattr(demo, "datetime", FixedDatetime)
    # Use the committed fixture, independent of market history in the dev DB.
    db.execute(delete(PriceSnapshot))
    fixture = json.loads(FIXTURE_PATH.read_text())
    stocks = {s.symbol: s for s in db.scalars(select(Stock)).all()}
    for symbol in demo.SCENARIO_FINAL:
        stock = stocks[symbol]
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

    demo.cmd_reset()
    reset_state = snapshot()
    demo.cmd_reset()
    assert snapshot() == reset_state
    demo.cmd_advance()
    first = snapshot()
    demo.cmd_advance()
    assert snapshot() == first
    demo.cmd_reset()
    demo.cmd_advance()
    assert snapshot() == first

    # Expected outputs from the committed market fixture and production engine.
    # These are assertions only; the demo never injects attention scores.
    # today, since, objective, momentum relevance/final/band, stability equivalents
    expected = {
        "RELIANCE": (6.27, 4.70, 80.0, (33.8, 100.0, "HIGH"), (18.8, 98.8, "HIGH")),
        "BEL": (4.13, 3.30, 76.7, (28.2, 100.0, "HIGH"), (13.2, 89.9, "HIGH")),
        "HDFCBANK": (-3.77, -2.80, 60.0, (16.2, 76.2, "MEDIUM"), (21.2, 81.2, "HIGH")),
        "TCS": (0.40, 0.20, 4.5, (0.8, 5.3, "LOW"), (0.8, 5.3, "LOW")),
        "TATASTEEL": (-0.60, -0.30, 10.8, (1.2, 12.0, "LOW"), (1.2, 12.0, "LOW")),
    }
    for symbol, scenario in demo.SCENARIO_FINAL.items():
        stock = stocks[symbol]
        features = extract_features(db, stock.id, uuid.UUID(demo.PRIMARY_DEMO_USER_ID))
        assert features.volume_ratio == pytest.approx(scenario["volume_multiplier"], abs=1e-5)
        # Latest cumulative volume must contain the whole intended session total.
        historical_average = demo.get_avg_historical_session_volume(db, stock.id)
        latest = demo.get_latest_snapshot(db, stock.id)
        assert latest.volume == int(historical_average * scenario["volume_multiplier"])
        a = first[demo.PRIMARY_DEMO_USER_ID][symbol]
        b = first[demo.STABILITY_DEMO_USER_ID][symbol]
        assert a["objective_score"] == b["objective_score"]
        assert a["current_price"] == b["current_price"]
        assert a["session_change_pct"] == b["session_change_pct"]
        assert a["since_last_view_pct"] == b["since_last_view_pct"]
        today, since, objective, momentum, stability = expected[symbol]
        for item, personal in [(a, momentum), (b, stability)]:
            assert item["session_change_pct"] == today
            assert item["since_last_view_pct"] == since
            assert item["objective_score"] == objective
            assert (item["preference_fit"], item["attention_score"], item["attention_level"]) == personal
        rows = db.scalars(select(PriceSnapshot).where(PriceSnapshot.stock_id == stock.id, PriceSnapshot.source == "mock")).all()
        assert len(rows) == 2


def test_demo_historical_volume_uses_latest_poll(monkeypatch):
    from types import SimpleNamespace
    snapshots = [SimpleNamespace(timestamp=datetime(2026, 9, day, hour, tzinfo=timezone.utc), volume=volume) for day, hour, volume in [(2, 5, 200), (2, 10, 1000), (3, 5, 300), (3, 10, 2000)]]
    monkeypatch.setattr(demo, "get_historical_snapshots_before_today", lambda db, stock_id: snapshots)
    assert demo.get_historical_session_volumes(None, None) == [1000, 2000]
    assert demo.get_avg_historical_session_volume(None, None) == 1500
