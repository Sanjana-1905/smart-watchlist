from app.main import app
from app.services.context_service import get_context_provider, FixtureContextProvider


def test_context_authenticated_and_fixture_provenance(client,auth_headers):
    assert client.get('/stocks/TCS/context').status_code == 401
    result=client.get('/stocks/TCS/context',headers=auth_headers)
    assert result.status_code==200
    data=result.json()
    assert data['status']=='AVAILABLE'
    assert 'fixture' in data['provenance'].lower()
    assert data['items'][0]['source']=='Tata Consultancy Services'
    assert data['items'][0]['url'].startswith('https://www.tcs.com/')
    assert FixtureContextProvider().get_context('UNKNOWN').status=='EMPTY'


def test_provider_failure_isolated_from_analytics_and_watchlist(client,auth_headers):
    class BrokenProvider:
        def get_context(self,symbol):
            raise RuntimeError('Simulated provider outage')
    app.dependency_overrides[get_context_provider]=lambda:BrokenProvider()
    try:
        context=client.get('/stocks/RELIANCE/context',headers=auth_headers)
        assert context.status_code==200
        assert context.json()['status']=='UNAVAILABLE'
        assert context.json()['items']==[]
        analytics=client.get('/stocks/RELIANCE/analytics',headers=auth_headers)
        assert analytics.status_code==200
        assert analytics.json()['availability']['analytics_available']
        assert client.get('/watchlist/changes',headers=auth_headers).status_code==200
    finally:
        app.dependency_overrides.pop(get_context_provider,None)
