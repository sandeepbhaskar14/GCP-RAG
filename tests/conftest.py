import pytest

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_current_firebase_user,
    require_verified_email,
)
from app.api.routes import auth
from app.db.session import get_db


@pytest.fixture
def firebase_user():
    """Sample decoded Firebase ID token claims."""

    return {
        "uid": "test-firebase-uid",
        "email": "test@example.com",
        "name": "Test User",
        "email_verified": True,
    }


@pytest.fixture
def app():
    """Create an isolated FastAPI application for testing."""

    test_app = FastAPI()

    # Include the actual authentication router.
    test_app.include_router(auth.router)

    # Endpoint protected by Firebase authentication.
    @test_app.get("/test/protected")
    def protected_route(
        firebase_user: dict = Depends(get_current_firebase_user),
    ):
        return {
            "message": "Authenticated successfully",
            "uid": firebase_user["uid"],
        }

    # Endpoint requiring verified email.
    @test_app.get("/test/verified")
    def verified_route(
        firebase_user: dict = Depends(require_verified_email),
    ):
        return {
            "message": "Email verified",
            "email": firebase_user["email"],
        }

    # Mock database dependency.
    def override_get_db():
        yield object()

    test_app.dependency_overrides[get_db] = override_get_db

    yield test_app

    # Remove overrides after tests.
    test_app.dependency_overrides.clear()


@pytest.fixture
def client(app):
    """Provide an HTTP client for the test application."""

    with TestClient(app) as test_client:
        yield test_client
