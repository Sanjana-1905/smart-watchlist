"""
API-level onboarding tests: authentication requirement, correct persistence,
and — most importantly — user isolation (one user's onboarding must never
touch another user's profile).

Run inside the backend container:
    docker compose exec backend pytest tests/test_onboarding_api.py -v
"""
import uuid


def _register(client) -> dict:
    """Registers a brand-new throwaway user and returns {'headers': ..., 'email': ...}."""
    email = f"test-{uuid.uuid4()}@example.com"
    res = client.post("/auth/register", json={"email": email, "password": "testpass123"})
    assert res.status_code == 201, res.text
    token = res.json()["access_token"]
    return {"headers": {"Authorization": f"Bearer {token}"}, "email": email}


class TestOnboardingAuth:
    def test_onboarding_requires_authentication(self, client):
        res = client.post(
            "/onboarding",
            json={
                "attention_priority": "UPWARD_MOVEMENT",
                "movement_sensitivity": "HIGH_MOVEMENT",
                "time_horizon": "SHORT_TERM",
            },
        )
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "MISSING_TOKEN"


class TestNewUserDefaults:
    def test_new_registration_has_onboarding_incomplete(self, client):
        user = _register(client)
        res = client.get("/auth/me", headers=user["headers"])
        assert res.status_code == 200
        assert res.json()["onboarding_completed"] is False


class TestOnboardingPersistence:
    def test_onboarding_updates_own_profile_and_marks_complete(self, client):
        user = _register(client)

        res = client.post(
            "/onboarding",
            json={
                "attention_priority": "UPWARD_MOVEMENT",
                "movement_sensitivity": "HIGH_MOVEMENT",
                "time_horizon": "SHORT_TERM",
            },
            headers=user["headers"],
        )
        assert res.status_code == 200
        body = res.json()
        assert body["attention_style"] == "MOMENTUM"
        assert body["risk_profile"] == "AGGRESSIVE"
        assert body["time_horizon"] == "SHORT_TERM"
        assert body["onboarding_completed"] is True

        me = client.get("/auth/me", headers=user["headers"]).json()
        assert me["onboarding_completed"] is True

        profile = client.get("/profile", headers=user["headers"]).json()
        assert profile["attention_style"] == "MOMENTUM"
        assert profile["risk_profile"] == "AGGRESSIVE"
        assert profile["onboarding_completed"] is True


class TestOnboardingUserIsolation:
    def test_user_a_onboarding_does_not_affect_user_b(self, client):
        user_a = _register(client)
        user_b = _register(client)

        # Only A completes onboarding, with answers that clearly diverge
        # from the BALANCED/BALANCED/LONG_TERM registration default.
        res = client.post(
            "/onboarding",
            json={
                "attention_priority": "DOWNSIDE_RISK",
                "movement_sensitivity": "SELECTIVE",
                "time_horizon": "LONG_TERM",
            },
            headers=user_a["headers"],
        )
        assert res.status_code == 200
        assert res.json()["attention_style"] == "STABILITY"

        # B must remain completely untouched.
        b_profile = client.get("/profile", headers=user_b["headers"]).json()
        assert b_profile["onboarding_completed"] is False
        assert b_profile["attention_style"] == "BALANCED"
        assert b_profile["risk_profile"] == "BALANCED"
        assert b_profile["time_horizon"] == "LONG_TERM"

        b_me = client.get("/auth/me", headers=user_b["headers"]).json()
        assert b_me["onboarding_completed"] is False
