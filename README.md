# TaskFlow

A distributed job processing platform that submits computational jobs from a web dashboard, tracks status, and views results.

## Quick start

The only requirement is [Docker Desktop](https://www.docker.com/products/docker-desktop/) (running). One command starts everything: Postgres, Redis, the API, the worker, and the dashboard.

```bash
git clone https://github.com/UmarJavaid56/Distributed-Job-Processing-Platform.git
cd Distributed-Job-Processing-Platform
docker compose up --build
```

When the logs settle, open:

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:3000 |
| API / Swagger | http://localhost:8000/docs |
| Health | http://localhost:8000/health |

Services start in order: the API waits for Postgres and Redis to pass healthchecks, and the worker and dashboard wait for the API.

Run more workers for concurrent processing:

```bash
docker compose up --build --scale worker=5
```

Stop everything with `docker compose down` (add `-v` to also delete the database).

## Architecture

```text
React (TypeScript)
        |
        |  REST (HTTP)
        v
   FastAPI backend
        |
        +----------> PostgreSQL   (durable job records)
        |
        +----------> Redis
                        |
                        |  job_queue (LPUSH / BRPOP)
                        v
                   Worker process
                        |
                        v
                   PostgreSQL
```

- The **frontend** never talks to PostgreSQL or Redis — only to the REST API.
- The **API** validates requests, writes jobs to Postgres, enqueues job IDs in Redis, and serves reads with a status cache.
- The **worker** is a separate process: it pops IDs from Redis, loads jobs from Postgres, runs the work, and updates status/results.

### Job state machine

```text
queued ──► running ──► completed
                └──► failed

queued ──► cancelled   (only while still queued)
```

Invalid transitions are rejected (e.g. cancelling a completed job returns **409 Conflict**).

## Tech stack

| Layer | Technology |
|-------|------------|
| API | Python, FastAPI, Pydantic, SQLAlchemy |
| Database | PostgreSQL |
| Queue & cache | Redis |
| Worker | Python process (`BRPOP` + DB updates) |
| Frontend | React, TypeScript, Vite |
| Infra | Docker, Docker Compose |
| Tests | pytest |

## Features

- Create jobs with a name and JSON payload
- List jobs with pagination (newest first)
- Get job details by ID
- Cancel queued jobs
- Background processing via Redis-backed workers
- Redis cache for single-job status reads
- Simple dashboard with polling for live status updates

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/jobs` | Create a job (`queued`), enqueue ID in Redis |
| `GET` | `/api/jobs` | List jobs (`?limit=20&offset=0`) |
| `GET` | `/api/jobs/{job_id}` | Get one job (cache-aside via Redis) |
| `DELETE` | `/api/jobs/{job_id}` | Cancel if status is `queued` |
| `GET` | `/health` | API health |
| `GET` | `/redis-health` | Redis connectivity check |
| `GET` | `/docs` | Interactive OpenAPI (Swagger) |

### Example: create a job

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"sleep-test\", \"payload\": {\"seconds\": 3}}"
```

### Example: get a job

```bash
curl http://localhost:8000/api/jobs/<job-id>
```

## Development setup (optional)

You don't need this to run the project; use the [Quick start](#quick-start). This setup runs the API, worker, and frontend outside Docker so code changes reload instantly while you edit.

### Prerequisites

- Python 3.12+
- Node.js 20+ (npm)
- Docker Desktop (for Postgres and Redis)

### 1. Start Postgres and Redis

```bash
docker compose up -d db redis
```

### 2. Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows: copy .env.example .env
```

Ensure `.env` uses the **psycopg3** URL scheme:

```env
DATABASE_URL=postgresql+psycopg://taskflow:taskflow@localhost:5432/taskflow
REDIS_URL=redis://localhost:6379/0
```

Run the API (from `backend/`):

```bash
uvicorn app.main:app --reload
```

Run the worker (second terminal, from `backend/`):

```bash
python -m app.workers.worker
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — the Vite app calls the API at `http://127.0.0.1:8000` by default.

Don't run this alongside the full Compose stack: both use ports 8000, 5432, and 6379.

Inside Compose, the API and worker reach Postgres/Redis by service name (`db`, `redis`) instead of `localhost`. The browser still calls `http://localhost:8000` (see the `VITE_API_URL` build arg).

## Running tests

From `backend/` (with the virtualenv activated):

```bash
pip install -r requirements.txt
pytest
pytest --cov=app --cov-report=term-missing
```

Tests use an in-memory SQLite database and mock Redis enqueue/cache calls, so Docker does not need to be running for the API suite. Current suite: **29** tests covering API, Redis cache helpers, and worker state transitions (~**97%** line coverage on `app/`).

### Load benchmark

With the stack up and workers scaled:

```bash
docker compose up --build -d --scale worker=5
python scripts/load_bench.py --url http://127.0.0.1:8000 --jobs 1000 --workers-hint 5
```

Example measured result: **1,000** jobs submitted, **5** concurrent workers, **100%** completed successfully (~67 jobs/sec wall-clock).

## Project structure

```text
taskflow/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── redis.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── routes/
│   │   └── workers/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── services/
│   │   └── types/
│   └── Dockerfile
├── scripts/
│   └── load_bench.py
├── docker-compose.yml
└── README.md
```

## Design Decisions

### Why PostgreSQL?

Jobs need durable history, as status, results, errors, and timestamps must survive restarts. Listing and filtering by `created_at` fit a relational model. Postgres is the **source of truth** so if Redis or a worker dies, job rows remain queryable.

### Why Redis?

Two roles, both ephemeral/fast:

1. **Queue** — `job_queue` holds pending job IDs (`LPUSH` on create, `BRPOP` in the worker). The API returns immediately without waiting for compute.
2. **Status cache** — `job_status:{id}` speeds up repeated `GET /api/jobs/{id}` with a short TTL, which is invalidated when status changes.

Redis is not used as the system of record. If Redis is empty, jobs still exist in Postgres (orphaned `queued` rows can be re-enqueued or skipped by policy).

### Why asynchronous workers?

Compute (even simulated sleep) must not block HTTP handlers. A separate worker process scales independently from the API, crashes without taking down request serving, and matches how real job systems separate “accept work” from “do work.”

### Why REST?

Simple to debug with curl/Swagger, easy for the React client, and enough for create/list/get/cancel. Polling covers live status for a dashboard without WebSockets or extra infrastructure.

### Why Docker?

Identical environments for Postgres, Redis, API, worker, and frontend. `docker compose up --build` demos the whole system without manual service installs. Compose keeps the project understandable — no Kubernetes.

### How job state transitions work?

1. **Create** — insert row as `queued`, push ID to Redis, return 201.
2. **Worker** — pop ID; if still `queued`, set `running` + `started_at`; run work; set `completed` + `result` or `failed` + `error`.
3. **Cancel** — only from `queued` → `cancelled` (409 otherwise). The worker skips non-queued IDs if they were already cancelled after enqueue.
4. **Cache** — GET may serve Redis; writes invalidate `job_status:{id}` so clients don’t see stale status.

