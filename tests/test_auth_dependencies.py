
import pytest

from firebase_admin import auth, exceptions

from app.api.dependencies import get_current_firebase_user
from app.api.routes import auth as auth_routes


# --------------------------------------------------
# 1. Authentication tests
# --------------------------------------------------

def test_missing_authorization_token(client):
    response = client.get("/test/protected")

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Authentication credentials are required."
    )


def test_invalid_token(client, monkeypatch):
    def mock_verify(token):
        raise auth.InvalidIdTokenError("Invalid token")

    monkeypatch.setattr(
        "app.api.dependencies.verify_firebase_id_token",
        mock_verify,
    )

    response = client.get(
        "/test/protected",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_expired_token(client, monkeypatch):
    def mock_verify(token):
        raise auth.ExpiredIdTokenError(
            "Token expired",
            ValueError("Expired token"),
        )

    monkeypatch.setattr(
        "app.api.dependencies.verify_firebase_id_token",
        mock_verify,
    )

    response = client.get(
        "/test/protected",
        headers={"Authorization": "Bearer expired-token"},
    )

    assert response.status_code == 401


def test_revoked_token(client, monkeypatch):
    def mock_verify(token):
        raise auth.RevokedIdTokenError("Token revoked")

    monkeypatch.setattr(
        "app.api.dependencies.verify_firebase_id_token",
        mock_verify,
    )

    response = client.get(
        "/test/protected",
        headers={"Authorization": "Bearer revoked-token"},
    )

    assert response.status_code == 401


def test_disabled_firebase_account(client, monkeypatch):
    def mock_verify(token):
        raise auth.UserDisabledError("Account disabled")

    monkeypatch.setattr(
        "app.api.dependencies.verify_firebase_id_token",
        mock_verify,
    )

    response = client.get(
        "/test/protected",
        headers={"Authorization": "Bearer disabled-token"},
    )

    assert response.status_code == 401


def test_value_error_returns_401(client, monkeypatch):
    def mock_verify(token):
        raise ValueError("Invalid token")

    monkeypatch.setattr(
        "app.api.dependencies.verify_firebase_id_token",
        mock_verify,
    )

    response = client.get(
        "/test/protected",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


# --------------------------------------------------
# 2. Firebase service failure
# --------------------------------------------------

def test_firebase_service_failure_returns_503(
    client,
    monkeypatch,
):
    def mock_verify(token):
        raise exceptions.FirebaseError(
            "internal-error",
            "Firebase unavailable",
        )

    monkeypatch.setattr(
        "app.api.dependencies.verify_firebase_id_token",
        mock_verify,
    )

    response = client.get(
        "/test/protected",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Authentication service temporarily unavailable."
    )


# --------------------------------------------------
# 3. Verified email tests
# --------------------------------------------------

def test_verified_email_is_allowed(
    client,
    monkeypatch,
    firebase_user,
):
    monkeypatch.setattr(
        "app.api.dependencies.verify_firebase_id_token",
        lambda token: firebase_user,
    )

    response = client.get(
        "/test/verified",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"


def test_unverified_email_is_rejected(
    client,
    monkeypatch,
    firebase_user,
):
    firebase_user["email_verified"] = False

    monkeypatch.setattr(
        "app.api.dependencies.verify_firebase_id_token",
        lambda token: firebase_user,
    )

    response = client.get(
        "/test/verified",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Please verify your email address before using this feature."
    )


# --------------------------------------------------
# 4. Successful authentication
# --------------------------------------------------

def test_valid_token_authentication(
    client,
    monkeypatch,
    firebase_user,
):
    monkeypatch.setattr(
        "app.api.dependencies.verify_firebase_id_token",
        lambda token: firebase_user,
    )

    response = client.get(
        "/test/protected",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    assert response.json()["uid"] == "test-firebase-uid"


# --------------------------------------------------
# 5. /auth/me integration tests
# --------------------------------------------------

def test_auth_me_returns_user_profile(
    client,
    monkeypatch,
    firebase_user,
):
    # Mock Firebase token verification.
    monkeypatch.setattr(
        "app.api.dependencies.verify_firebase_id_token",
        lambda token: firebase_user,
    )

    # Mock the PostgreSQL user lookup/create operation.
    class MockUser:
        id = "55429899-90a0-45c6-b207-d0c54ba40e2b"
        firebase_uid = "test-firebase-uid"
        email = "test@example.com"
        name = "Test User"
        subscription_tier = "free"
        user_role = "user"

    monkeypatch.setattr(
        auth_routes,
        "get_or_create_user_from_firebase",
        lambda **kwargs: MockUser(),
    )

    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["firebase_uid"] == "test-firebase-uid"
    assert data["email"] == "test@example.com"
    assert data["subscription_tier"] == "free"
    assert data["user_role"] == "user"


def test_auth_me_returns_same_user_id_on_repeated_requests(
    client,
    monkeypatch,
    firebase_user,
):
    monkeypatch.setattr(
        "app.api.dependencies.verify_firebase_id_token",
        lambda token: firebase_user,
    )

    class MockUser:
        id = "55429899-90a0-45c6-b207-d0c54ba40e2b"
        firebase_uid = "test-firebase-uid"
        email = "test@example.com"
        name = "Test User"
        subscription_tier = "free"
        user_role = "user"

    monkeypatch.setattr(
        auth_routes,
        "get_or_create_user_from_firebase",
        lambda **kwargs: MockUser(),
    )

    headers = {"Authorization": "Bearer valid-token"}

    response_1 = client.get("/auth/me", headers=headers)
    response_2 = client.get("/auth/me", headers=headers)

    assert response_1.status_code == 200
    assert response_2.status_code == 200

    assert response_1.json()["id"] == response_2.json()["id"]
