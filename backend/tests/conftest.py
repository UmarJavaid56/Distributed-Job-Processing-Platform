import os

# Must be set before importing app modules (Settings reads env on import).
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["APP_NAME"] = "TaskFlow-Test"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Re-bind the database module to an in-memory SQLite engine shared across the app.
import app.database as database_module
from app.database import Base, get_db
from app.models.job import Job  # noqa: F401 — register model with Base.metadata

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

database_module.engine = test_engine
database_module.session_Local = TestingSessionLocal

Base.metadata.create_all(bind=test_engine)

from app.main import app  # noqa: E402 — import after engine override


@pytest.fixture()
def db_session():
    """Fresh tables for each test."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session, monkeypatch):
    """HTTP client with test DB and Redis side effects disabled."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    monkeypatch.setattr("app.routes.jobs.enqueue_job", lambda job_id: None)
    monkeypatch.setattr("app.routes.jobs.get_cached_job", lambda job_id: None)
    monkeypatch.setattr("app.routes.jobs.set_cached_job", lambda job: None)
    monkeypatch.setattr("app.routes.jobs.invalidated_job_cache", lambda job_id: None)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
