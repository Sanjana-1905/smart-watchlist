import uuid
from datetime import datetime, timezone
import pytest
from app.models import Stock, User, UserProfile, UserViewState, PriceSnapshot
from app.core.security import create_access_token
from tests.test_scoring_regressions import isolated_db  # noqa: F401

@pytest.fixture
def scenario(isolated_db):
    db = isolated_db
    stock = Stock(id=uuid.uuid4(), symbol='AN' + uuid.uuid4().hex[:8].upper(), company_name='Analytics test', exchange='NSE')
    users = [User(id=uuid.uuid4()), User(id=uuid.uuid4())]
    db.add_all([stock, *users]); db.flush()
    for user, price, style in zip(users, [100, 102], ['MOMENTUM', 'STABILITY']):
        db.add(UserProfile(user_id=user.id, risk_profile='AGGRESSIVE', attention_style=style, time_horizon='SHORT_TERM'))
        db.add(UserViewState(user_id=user.id, stock_id=stock.id, last_viewed_price=price, last_viewed_at=datetime(2026,9,2,tzinfo=timezone.utc)))
    for day, hour, price, volume in [(3,5,99,400),(3,10,100,1000),(4,5,102,500),(4,10,104,2000)]:
        db.add(PriceSnapshot(stock_id=stock.id,timestamp=datetime(2026,9,day,hour,tzinfo=timezone.utc),open=price,high=price,low=price,close=price,volume=volume,source='mock'))
    db.commit()
    return stock, users, [{'Authorization':'Bearer '+create_access_token(u.id)} for u in users]

def test_analytics_requires_jwt(client):
    assert client.get('/stocks/RELIANCE/analytics').status_code == 401

def test_analytics_canonical_inputs_decomposition_and_read_only(client, isolated_db, scenario):
    stock, users, headers = scenario
    results = [client.get(f'/stocks/{stock.symbol}/analytics',headers=h) for h in headers]
    assert all(r.status_code == 200 for r in results)
    a,b = [r.json() for r in results]
    assert not a['identity']['is_in_watchlist']  # Unwatched still analyzable.
    assert a['temporal']['previous_session_close'] == 100
    assert a['temporal']['previous_session_date'] == '2026-09-03'
    assert a['temporal']['session_change_pct'] == pytest.approx(4)
    assert a['temporal']['last_viewed_price'] == 100
    assert b['temporal']['last_viewed_price'] == 102
    assert a['temporal']['since_last_view_pct'] == pytest.approx(4)
    assert b['temporal']['since_last_view_pct'] == pytest.approx((104/102-1)*100)
    assert a['volume'] == dict(current_session_volume=2000,baseline_average_volume=1000,baseline_sample_count=1,volume_ratio=2)
    assert a['volatility']['canonical_value'] == .005
    assert a['volatility']['floor_applied'] is True
    assert a['volatility']['sample_count'] == 1
    assert a['volatility']['unusualness_ratio'] == pytest.approx(8)
    assert a['technical']['previous_window_max_close'] == 100
    assert a['technical']['sample_count'] == 1
    assert a['technical']['is_new_high'] is True

    assert a['attention'] == b['attention']
    assert a['personal'] != b['personal']
    for data in [a,b]:
        obj, personal, final = data['attention'],data['personal'],data['final']
        assert obj['objective_exact'] == pytest.approx(obj['return_contribution']+obj['volume_contribution']+obj['technical_contribution'])
        assert personal['personal_exact'] == pytest.approx(personal['since_view_contribution']+personal['profile_contribution'])
        assert final['attention_score'] == round(min(obj['objective_exact']+personal['personal_exact'],100),1)
    isolated_db.expire_all()
    assert [float(isolated_db.get(UserViewState,(u.id,stock.id)).last_viewed_price) for u in users] == [100,102]
    assert len(a['history']) == 4
    assert a['observation']['freshness']['source'] == 'mock'

def test_analytics_no_baseline(client, isolated_db, scenario):
    stock, users, headers = scenario
    isolated_db.delete(isolated_db.get(UserViewState,(users[0].id,stock.id))); isolated_db.commit()
    data=client.get(f'/stocks/{stock.symbol}/analytics',headers=headers[0]).json()
    assert data['temporal']['last_viewed_at'] is None
    assert data['temporal']['since_last_view_pct'] is None
    assert data['personal']['since_view_contribution'] == 0

def test_analytics_insufficient_history(client, isolated_db, scenario):
    _,_,headers=scenario
    empty=Stock(id=uuid.uuid4(),symbol='EMPTY'+uuid.uuid4().hex[:6].upper(),company_name='No observations',exchange='NSE')
    isolated_db.add(empty);isolated_db.commit()
    data=client.get(f'/stocks/{empty.symbol}/analytics',headers=headers[0]).json()
    assert data['availability']['analytics_available'] is False
    assert data['observation']['current_price'] is None
    assert data['final'] is None
    assert data['attention'] is None
    assert data['volume']['volume_ratio'] is None

def test_analytics_transaction_is_read_only_snapshot(client, auth_headers, monkeypatch):
    from sqlalchemy import text
    from app.services import analytics_service
    original = analytics_service.stock_repository.get_history
    def inspect(db, stock_id):
        assert db.scalar(text('SHOW transaction_read_only')) == 'on'
        assert db.scalar(text('SHOW transaction_isolation')) == 'repeatable read'
        return original(db, stock_id)
    monkeypatch.setattr(analytics_service.stock_repository, 'get_history', inspect)
    assert client.get('/stocks/RELIANCE/analytics', headers=auth_headers).status_code == 200

def test_multiple_observations_one_session_still_unavailable(client, isolated_db, scenario):
    _, _, headers = scenario
    stock=Stock(id=uuid.uuid4(),symbol='ONE'+uuid.uuid4().hex[:6].upper(),company_name='One session',exchange='NSE')
    isolated_db.add(stock);isolated_db.flush()
    for hour in [5,10]:
        isolated_db.add(PriceSnapshot(stock_id=stock.id,timestamp=datetime(2026,9,3,hour,tzinfo=timezone.utc),open=100,high=100,low=100,close=100,volume=1000,source='mock'))
    isolated_db.commit()
    data=client.get(f'/stocks/{stock.symbol}/analytics',headers=headers[0]).json()
    assert data['observation']['current_price']==100
    assert not data['availability']['analytics_available']
    assert data['temporal']['previous_session_close'] is None
    assert data['final'] is None
