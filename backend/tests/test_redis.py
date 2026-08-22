from datetime import datetime, timezone
from unittest.mock import MagicMock
import uuid

from app.models.job import JobStatus
from app.redis import (
    get_cached_job,
    invalidated_job_cache,
    job_cache_key,
    set_cached_job,
)
from app.schemas.job import JobRead


def _sample_job_read():
    return JobRead(
        id=uuid.uuid4(),
        name="cached",
        payload={"seconds": 1},
        status=JobStatus.queued,
        result=None,
        error=None,
        created_at=datetime.now(timezone.utc),
        started_at=None,
        completed_at=None,
    )


def test_job_cache_key():
    job_id = uuid.uuid4()
    assert job_cache_key(job_id) == f"job_status:{job_id}"


def test_get_cached_job_hit(monkeypatch):
    job = _sample_job_read()
    client = MagicMock()
    client.get.return_value = job.model_dump_json()
    monkeypatch.setattr("app.redis.redis_client", client)

    cached = get_cached_job(job.id)
    assert cached is not None
    assert cached.id == job.id
    assert cached.name == "cached"


def test_get_cached_job_miss(monkeypatch):
    client = MagicMock()
    client.get.return_value = None
    monkeypatch.setattr("app.redis.redis_client", client)

    assert get_cached_job(uuid.uuid4()) is None


def test_get_cached_job_soft_fails(monkeypatch):
    client = MagicMock()
    client.get.side_effect = RuntimeError("down")
    monkeypatch.setattr("app.redis.redis_client", client)

    assert get_cached_job(uuid.uuid4()) is None


def test_set_cached_job(monkeypatch):
    job = _sample_job_read()
    client = MagicMock()
    monkeypatch.setattr("app.redis.redis_client", client)

    set_cached_job(job)
    client.set.assert_called_once()
    args, kwargs = client.set.call_args
    assert args[0] == job_cache_key(job.id)
    assert kwargs["ex"] == 60


def test_set_cached_job_soft_fails(monkeypatch):
    job = _sample_job_read()
    client = MagicMock()
    client.set.side_effect = RuntimeError("down")
    monkeypatch.setattr("app.redis.redis_client", client)

    assert set_cached_job(job) is None


def test_invalidate_job_cache(monkeypatch):
    job_id = uuid.uuid4()
    client = MagicMock()
    monkeypatch.setattr("app.redis.redis_client", client)

    invalidated_job_cache(job_id)
    client.delete.assert_called_once_with(job_cache_key(job_id))


def test_invalidate_job_cache_soft_fails(monkeypatch):
    client = MagicMock()
    client.delete.side_effect = RuntimeError("down")
    monkeypatch.setattr("app.redis.redis_client", client)

    assert invalidated_job_cache(uuid.uuid4()) is None
