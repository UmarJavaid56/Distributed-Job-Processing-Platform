import uuid

from app.models.job import Job, JobStatus


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_job(client):
    response = client.post(
        "/api/jobs",
        json={"name": "sleep-test", "payload": {"seconds": 2}},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "sleep-test"
    assert data["payload"] == {"seconds": 2}
    assert data["status"] == "queued"
    assert data["id"]
    assert data["result"] is None


def test_create_job_validation_error(client):
    response = client.post("/api/jobs", json={"payload": {"seconds": 1}})
    assert response.status_code == 422


def test_get_job(client):
    created = client.post(
        "/api/jobs",
        json={"name": "get-me", "payload": {}},
    ).json()

    response = client.get(f"/api/jobs/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["name"] == "get-me"


def test_get_job_not_found(client):
    missing = uuid.uuid4()
    response = client.get(f"/api/jobs/{missing}")
    assert response.status_code == 404


def test_get_job_invalid_uuid(client):
    response = client.get("/api/jobs/not-a-uuid")
    assert response.status_code == 422


def test_list_jobs_order_and_pagination(client):
    client.post("/api/jobs", json={"name": "first", "payload": {}})
    client.post("/api/jobs", json={"name": "second", "payload": {}})
    client.post("/api/jobs", json={"name": "third", "payload": {}})

    response = client.get("/api/jobs?limit=2&offset=0")
    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) == 2
    # Newest first
    assert jobs[0]["name"] == "third"
    assert jobs[1]["name"] == "second"

    page2 = client.get("/api/jobs?limit=2&offset=2").json()
    assert len(page2) == 1
    assert page2[0]["name"] == "first"


def test_cancel_queued_job(client):
    created = client.post(
        "/api/jobs",
        json={"name": "cancel-me", "payload": {}},
    ).json()

    response = client.delete(f"/api/jobs/{created['id']}")
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert response.json()["completed_at"] is not None


def test_cancel_non_queued_job_conflict(client, db_session):
    created = client.post(
        "/api/jobs",
        json={"name": "already-done", "payload": {}},
    ).json()

    job = db_session.get(Job, uuid.UUID(created["id"]))
    job.status = JobStatus.completed
    db_session.commit()

    response = client.delete(f"/api/jobs/{created['id']}")
    assert response.status_code == 409


def test_cancel_missing_job(client):
    response = client.delete(f"/api/jobs/{uuid.uuid4()}")
    assert response.status_code == 404


def test_get_job_cache_hit(client, monkeypatch):
    from app.schemas.job import JobRead

    created = client.post(
        "/api/jobs",
        json={"name": "from-cache", "payload": {"seconds": 1}},
    ).json()

    monkeypatch.setattr(
        "app.routes.jobs.get_cached_job",
        lambda _job_id: JobRead.model_validate(created),
    )

    response = client.get(f"/api/jobs/{created['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "from-cache"


def test_list_jobs_empty(client):
    response = client.get("/api/jobs")
    assert response.status_code == 200
    assert response.json() == []


def test_redis_health(client, monkeypatch):
    monkeypatch.setattr("app.main.redis_client.ping", lambda: True)
    response = client.get("/redis-health")
    assert response.status_code == 200
    assert response.json() == {"redis": "ok"}


def test_redis_health_unavailable(client, monkeypatch):
    monkeypatch.setattr("app.main.redis_client.ping", lambda: False)
    response = client.get("/redis-health")
    assert response.status_code == 503


def test_items_db_probe(client):
    response = client.get("/items")
    assert response.status_code == 200
    assert "message" in response.json()
