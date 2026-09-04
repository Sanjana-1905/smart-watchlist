"""
Phase 10 resilience tests: error envelope shape, duplicate-add rejection,
idempotent retries, optimistic-concurrency conflicts, health check honesty,
and circuit-breaker behavior.

Run inside the backend container so 'db'/'redis' hostnames resolve:
    docker compose exec backend pytest tests/test_resilience.py -v
"""
import uuid


class TestErrorEnvelope:
    def test_404_uses_flat_error_envelope(self, client):
        res = client.get("/stocks/NOTAREALSYMBOL")
        assert res.status_code == 404
        body = res.json()
        assert "error" in body, "Response must use {'error': {...}}, not nest under 'detail'"
        assert "detail" not in body
        assert body["error"]["code"] == "STOCK_NOT_FOUND"

    def test_watchlist_item_not_found_envelope(self, client, unwatchlisted_symbol):
        res = client.delete(f"/watchlist/items/{unwatchlisted_symbol}")
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "WATCHLIST_ITEM_NOT_FOUND"


class TestDuplicateWatchlist:
    def test_duplicate_add_rejected_with_409(self, client, unwatchlisted_symbol):
        first = client.post("/watchlist/items", json={"symbol": unwatchlisted_symbol})
        assert first.status_code == 201

        second = client.post("/watchlist/items", json={"symbol": unwatchlisted_symbol})
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "WATCHLIST_DUPLICATE"


class TestIdempotency:
    def test_same_key_returns_identical_result_not_a_duplicate_error(self, client, unwatchlisted_symbol):
        key = str(uuid.uuid4())
        headers = {"Idempotency-Key": key}

        first = client.post("/watchlist/items", json={"symbol": unwatchlisted_symbol}, headers=headers)
        assert first.status_code == 201

        second = client.post("/watchlist/items", json={"symbol": unwatchlisted_symbol}, headers=headers)
        assert second.status_code == 201
        assert second.json() == first.json(), \
            "Retrying with the same Idempotency-Key must replay the original result"

    def test_different_key_hits_real_business_rules(self, client, unwatchlisted_symbol):
        first = client.post(
            "/watchlist/items", json={"symbol": unwatchlisted_symbol},
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )
        assert first.status_code == 201

        second = client.post(
            "/watchlist/items", json={"symbol": unwatchlisted_symbol},
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )
        assert second.status_code == 409, \
            "A different idempotency key must not bypass the real duplicate check"


class TestProfileConcurrency:
    def test_wrong_version_returns_409(self, client):
        current = client.get("/profile").json()
        wrong_version = current["version"] + 999

        res = client.put(
            "/profile",
            json={
                "risk_profile": current["risk_profile"],
                "attention_style": current["attention_style"],
                "time_horizon": current["time_horizon"],
            },
            headers={"If-Match": str(wrong_version)},
        )
        assert res.status_code == 409
        assert res.json()["error"]["code"] == "VERSION_CONFLICT"

    def test_correct_version_succeeds_and_increments(self, client):
        current = client.get("/profile").json()
        res = client.put(
            "/profile",
            json={
                "risk_profile": current["risk_profile"],
                "attention_style": current["attention_style"],
                "time_horizon": current["time_horizon"],
            },
            headers={"If-Match": str(current["version"])},
        )
        assert res.status_code == 200
        assert res.json()["version"] == current["version"] + 1


class TestHealthCheck:
    def test_health_returns_healthy_when_dependencies_ok(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "healthy"
        assert body["components"]["database"] == "healthy"
        assert body["components"]["redis"] == "healthy"


class TestValidationErrorEnvelope:
    def test_missing_required_field_uses_error_envelope(self, client):
        res = client.post("/watchlist/items", json={})
        assert res.status_code == 422
        body = res.json()
        assert "error" in body
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert "detail" not in body


class TestCircuitBreaker:
    def test_circuit_opens_after_consecutive_failures(self, redis_client):
        from app.providers.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(redis_client, "test_provider_transient")
        assert breaker.is_open() is False

        breaker.record_failure()
        breaker.record_failure()
        assert breaker.is_open() is False, "Should stay closed below threshold (3)"

        breaker.record_failure()
        assert breaker.is_open() is True, "Should open at the failure threshold"

        redis_client.delete("provider:test_provider_transient:failures")
        redis_client.delete("provider:test_provider_transient:circuit_until")

    def test_success_resets_failure_count(self, redis_client):
        from app.providers.circuit_breaker import CircuitBreaker

        breaker = CircuitBreaker(redis_client, "test_provider_recovery")
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_success()

        assert redis_client.get("provider:test_provider_recovery:failures") is None

        redis_client.delete("provider:test_provider_recovery:failures")
        redis_client.delete("provider:test_provider_recovery:circuit_until")
