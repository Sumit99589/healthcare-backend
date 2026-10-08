import pytest
from django.contrib.auth import get_user_model
from rest_framework.throttling import ScopedRateThrottle

from conftest import PASSWORD

REGISTER = "/api/auth/register/"
LOGIN = "/api/auth/login/"
REFRESH = "/api/auth/token/refresh/"
LOGOUT = "/api/auth/logout/"
ME = "/api/auth/me/"

User = get_user_model()
pytestmark = pytest.mark.django_db


def register(client, **overrides):
    payload = {"name": "Priya Nair", "email": "priya@example.com", "password": PASSWORD}
    payload.update(overrides)
    return client.post(REGISTER, payload)


class TestRegister:
    def test_creates_user_and_returns_tokens(self, api_client):
        response = register(api_client)

        assert response.status_code == 201
        body = response.json()
        assert body["user"]["name"] == "Priya Nair"
        assert body["user"]["email"] == "priya@example.com"
        assert set(body["tokens"]) == {"access", "refresh"}
        assert "password" not in body["user"]

        user = User.objects.get(email="priya@example.com")
        assert user.check_password(PASSWORD)
        assert user.password != PASSWORD  # stored hashed

    def test_returned_access_token_works(self, api_client):
        access = register(api_client).json()["tokens"]["access"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = api_client.get(ME)

        assert response.status_code == 200
        assert response.json()["email"] == "priya@example.com"

    def test_email_is_normalised_to_lowercase(self, api_client):
        response = register(api_client, email="  Priya@Example.COM ")

        assert response.status_code == 201
        assert response.json()["user"]["email"] == "priya@example.com"

    def test_duplicate_email_is_rejected_case_insensitively(self, api_client, user):
        response = register(api_client, email=user.email.upper())

        assert response.status_code == 400
        error = response.json()["error"]
        assert error["code"] == "validation_error"
        assert error["details"]["email"] == ["A user with this email already exists."]
        assert error["message"] == "email: A user with this email already exists."

    def test_missing_fields(self, api_client):
        response = api_client.post(REGISTER, {})

        assert response.status_code == 400
        details = response.json()["error"]["details"]
        assert set(details) == {"name", "email", "password"}

    @pytest.mark.parametrize(
        "password, reason",
        [
            ("short1!", "too short"),
            ("12345678901", "entirely numeric"),
            ("password123", "too common"),
            ("priyanair2026", "too similar"),
        ],
    )
    def test_weak_passwords_are_rejected(self, api_client, password, reason):
        response = register(api_client, password=password)

        assert response.status_code == 400
        messages = " ".join(response.json()["error"]["details"]["password"])
        assert reason in messages

    def test_invalid_email(self, api_client):
        response = register(api_client, email="not-an-email")

        assert response.status_code == 400
        assert "email" in response.json()["error"]["details"]

    def test_blank_name(self, api_client):
        response = register(api_client, name="   ")

        assert response.status_code == 400
        assert "name" in response.json()["error"]["details"]


class TestLogin:
    def test_returns_tokens_and_user(self, api_client, user):
        response = api_client.post(LOGIN, {"email": user.email, "password": PASSWORD})

        assert response.status_code == 200
        body = response.json()
        assert body["user"]["id"] == user.id
        assert set(body["tokens"]) == {"access", "refresh"}

    def test_email_is_case_insensitive(self, api_client, user):
        response = api_client.post(LOGIN, {"email": "ALICE@example.com", "password": PASSWORD})

        assert response.status_code == 200

    def test_wrong_password(self, api_client, user):
        response = api_client.post(LOGIN, {"email": user.email, "password": "wrong-password"})

        assert response.status_code == 401
        error = response.json()["error"]
        assert error["code"] == "no_active_account"
        assert error["message"] == "Invalid email or password."

    def test_unknown_email_gets_the_same_answer(self, api_client, db):
        response = api_client.post(LOGIN, {"email": "ghost@example.com", "password": PASSWORD})

        assert response.status_code == 401
        assert response.json()["error"]["message"] == "Invalid email or password."

    def test_inactive_user_cannot_log_in(self, api_client, make_user):
        make_user(email="gone@example.com", is_active=False)

        response = api_client.post(LOGIN, {"email": "gone@example.com", "password": PASSWORD})

        assert response.status_code == 401

    def test_missing_fields(self, api_client, db):
        response = api_client.post(LOGIN, {})

        assert response.status_code == 400
        assert set(response.json()["error"]["details"]) == {"email", "password"}

    def test_updates_last_login(self, api_client, user):
        assert user.last_login is None

        api_client.post(LOGIN, {"email": user.email, "password": PASSWORD})

        user.refresh_from_db()
        assert user.last_login is not None


class TestTokens:
    def _login(self, client, user):
        return client.post(LOGIN, {"email": user.email, "password": PASSWORD}).json()["tokens"]

    def test_refresh_rotates_and_blacklists_old_token(self, api_client, user):
        tokens = self._login(api_client, user)

        first = api_client.post(REFRESH, {"refresh": tokens["refresh"]})
        assert first.status_code == 200
        assert set(first.json()) == {"access", "refresh"}

        reused = api_client.post(REFRESH, {"refresh": tokens["refresh"]})
        assert reused.status_code == 401
        assert reused.json()["error"]["code"] == "token_not_valid"

    def test_logout_revokes_refresh_token(self, api_client, user):
        tokens = self._login(api_client, user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        assert api_client.post(LOGOUT, {"refresh": tokens["refresh"]}).status_code == 205
        assert api_client.post(REFRESH, {"refresh": tokens["refresh"]}).status_code == 401

    def test_cannot_revoke_someone_elses_token(self, api_client, auth_client, other_user):
        their_refresh = self._login(api_client, other_user)["refresh"]

        response = auth_client.post(LOGOUT, {"refresh": their_refresh})

        assert response.status_code == 403

    def test_logout_with_garbage_token(self, auth_client):
        response = auth_client.post(LOGOUT, {"refresh": "not-a-token"})

        assert response.status_code == 400
        assert "refresh" in response.json()["error"]["details"]

    def test_me_requires_authentication(self, api_client):
        response = api_client.get(ME)

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "not_authenticated"

    def test_invalid_access_token(self, api_client, db):
        api_client.credentials(HTTP_AUTHORIZATION="Bearer abc.def.ghi")

        response = api_client.get(ME)

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "token_not_valid"


def test_auth_endpoints_are_rate_limited(api_client, user, monkeypatch):
    monkeypatch.setitem(ScopedRateThrottle.THROTTLE_RATES, "auth", "3/min")
    payload = {"email": user.email, "password": "wrong-password"}

    statuses = [api_client.post(LOGIN, payload).status_code for _ in range(4)]

    assert statuses == [401, 401, 401, 429]
