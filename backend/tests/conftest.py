"""Shared fixtures for offline API tests — no live Stripe, Neon, or Auth0."""

import os

# Must run before any app import so pydantic-settings picks these over .env.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ.setdefault("AUTH0_DOMAIN", "test.auth0.com")
os.environ.setdefault("AUTH0_AUDIENCE", "https://test-api")
os.environ.setdefault("STRIPE_SECRET_KEY", "")
os.environ.setdefault("STRIPE_PRICE_ID", "")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.db import get_session
from app.core.security import AuthenticatedUser, get_current_user, get_optional_user
from app.main import app
from app.models.user import Tier, User

TEST_USER = AuthenticatedUser(auth0_sub="auth0|billing-test", email="billing@test.example")


@pytest.fixture
def engine():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)
    return test_engine


@pytest.fixture
def session(engine):
    with Session(engine) as db:
        yield db


@pytest.fixture
def client(session):
    def override_get_session():
        yield session

    def override_get_user():
        return TEST_USER

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = override_get_user
    # get_optional_user (M2.2) is a separate FastAPI dependency, not a
    # thin wrapper resolved through get_current_user's own override —
    # real test-suite regression found here: overriding only
    # get_current_user left every route using get_optional_user
    # (list_inquiries, get_inquiry, get_thread) doing real JWT
    # verification against a fake test token, breaking 12 existing tests
    # that assumed TEST_USER's identity everywhere. Overridden
    # independently, to the same identity, so both dependencies agree.
    app.dependency_overrides[get_optional_user] = override_get_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def pro_user(session):
    user = User(auth0_sub=TEST_USER.auth0_sub, email=TEST_USER.email or "", tier=Tier.pro)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
