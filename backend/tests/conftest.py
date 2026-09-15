"""
Shared fixtures.

These tests run inside the backend container against the real Postgres/Redis
from docker-compose (there's no separate test database in this prototype —
see docs/security.md for why that's an accepted tradeoff here, not something
you'd do in production). Run `python -m app.core.seed` at least once before
running the test suite so the demo user tests depend on exists.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
