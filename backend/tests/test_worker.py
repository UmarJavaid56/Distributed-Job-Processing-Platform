import uuid

import pytest

from app.models.job import Job, JobStatus
from app.workers.worker import process_job_id, run_worker


def _bind_worker_db(monkeypatch, db_session):
    """Use the test session without closing it (fixture owns lifecycle)."""
    monkeypatch.setattr(db_session, "close", lambda: None)
    monkeypatch.setattr("app.workers.worker.session_Local", lambda: db_session)
    monkeypatch.setattr("app.workers.worker.invalidated_job_cache", lambda _id: None)


def _make_job(db_session, *, status=JobStatus.queued, payload=None, name="work"):
    job = Job(name=name, payload=payload or {"seconds": 0}, status=status)
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def test_process_completes_queued_job(db_session, monkeypatch):
    _bind_worker_db(monkeypatch, db_session)

    job = _make_job(db_session)
    outcome = process_job_id(str(job.id))

    assert outcome == "completed"
    db_session.refresh(job)
    assert job.status == JobStatus.completed
    assert job.result is not None
    assert job.started_at is not None
    assert job.completed_at is not None


def test_process_skips_missing_job(db_session, monkeypatch):
    _bind_worker_db(monkeypatch, db_session)

    outcome = process_job_id(str(uuid.uuid4()))
    assert outcome == "skipped"


def test_process_skips_cancelled_job(db_session, monkeypatch):
    _bind_worker_db(monkeypatch, db_session)

    job = _make_job(db_session, status=JobStatus.cancelled)
    outcome = process_job_id(str(job.id))

    assert outcome == "skipped"
    db_session.refresh(job)
    assert job.status == JobStatus.cancelled


def test_process_marks_failed_on_work_error(db_session, monkeypatch):
    _bind_worker_db(monkeypatch, db_session)

    def boom(_seconds):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.workers.worker.time.sleep", boom)

    job = _make_job(db_session, payload={"seconds": 1})
    outcome = process_job_id(str(job.id))

    assert outcome == "failed"
    db_session.refresh(job)
    assert job.status == JobStatus.failed
    assert "boom" in (job.error or "")


def test_run_worker_processes_one_then_stops(db_session, monkeypatch):
    _bind_worker_db(monkeypatch, db_session)

    job = _make_job(db_session)
    calls = {"n": 0}

    def fake_brpop(_key, timeout=5):
        calls["n"] += 1
        if calls["n"] == 1:
            return ("job_queue", str(job.id))
        raise KeyboardInterrupt()

    monkeypatch.setattr("app.workers.worker.redis_client.brpop", fake_brpop)

    with pytest.raises(KeyboardInterrupt):
        run_worker()

    db_session.refresh(job)
    assert job.status == JobStatus.completed


def test_run_worker_continues_on_redis_timeout(monkeypatch):
    import redis as redis_lib

    calls = {"n": 0}

    def fake_brpop(_key, timeout=5):
        calls["n"] += 1
        if calls["n"] == 1:
            raise redis_lib.TimeoutError()
        raise KeyboardInterrupt()

    monkeypatch.setattr("app.workers.worker.redis_client.brpop", fake_brpop)

    with pytest.raises(KeyboardInterrupt):
        run_worker()

    assert calls["n"] == 2
