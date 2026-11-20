"""Shared test fixtures."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.categorias.service import seed_missing_categories
from app.database import get_session
from app.main import app

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture()
def db_session():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed_missing_categories(session)
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture()
def client(db_session):
    def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def registered_user(client):
    """Register a user and return credentials."""
    payload = {"username": "testuser", "email": "test@example.com", "password": "Secret123!"}
    client.post("/auth/register", json=payload)
    return payload


@pytest.fixture()
def auth_headers(client, registered_user):
    """Return Authorization headers for the registered user."""
    resp = client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
