"""
Submit N jobs and wait until they leave queued/running.

Usage (API + workers already running):
  python scripts/load_bench.py --url http://127.0.0.1:8000 --jobs 1000 --workers-hint 5
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter


def _request(method: str, url: str, body: dict | None = None) -> tuple[int, dict | list]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
        return resp.status, json.loads(raw) if raw else {}


def create_job(base: str, index: int) -> str:
    status, payload = _request(
        "POST",
        f"{base}/api/jobs",
        {"name": f"bench-{index}", "payload": {"seconds": 0}},
    )
    if status != 201:
        raise RuntimeError(f"create failed: {status} {payload}")
    return payload["id"]


def get_job(base: str, job_id: str) -> dict:
    status, payload = _request("GET", f"{base}/api/jobs/{job_id}")
    if status != 200:
        raise RuntimeError(f"get failed: {status} {payload}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="TaskFlow load benchmark")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--jobs", type=int, default=1000)
    parser.add_argument("--submit-concurrency", type=int, default=32)
    parser.add_argument("--timeout-sec", type=int, default=300)
    parser.add_argument("--workers-hint", type=int, default=5)
    args = parser.parse_args()
    base = args.url.rstrip("/")

    print(f"Health check {base}/health ...")
    try:
        code, health = _request("GET", f"{base}/health")
    except urllib.error.URLError as exc:
        print(f"API not reachable: {exc}", file=sys.stderr)
        return 1
    print(f"  {code} {health}")

    print(f"Submitting {args.jobs} jobs (concurrency={args.submit_concurrency}) ...")
    t0 = time.perf_counter()
    job_ids: list[str] = []
    errors = 0
    with ThreadPoolExecutor(max_workers=args.submit_concurrency) as pool:
        futures = [pool.submit(create_job, base, i) for i in range(args.jobs)]
        for fut in as_completed(futures):
            try:
                job_ids.append(fut.result())
            except Exception as exc:
                errors += 1
                print(f"  submit error: {exc}", file=sys.stderr)
    submit_s = time.perf_counter() - t0
    print(f"  submitted={len(job_ids)} errors={errors} in {submit_s:.2f}s")

    if not job_ids:
        return 1

    print("Waiting for terminal statuses ...")
    pending = set(job_ids)
    counts: Counter[str] = Counter()
    deadline = time.time() + args.timeout_sec
    while pending and time.time() < deadline:
        done_now: list[str] = []
        for job_id in list(pending):
            job = get_job(base, job_id)
            status = job["status"]
            if status in {"completed", "failed", "cancelled"}:
                counts[status] += 1
                done_now.append(job_id)
        for job_id in done_now:
            pending.remove(job_id)
        if pending:
            time.sleep(0.25)
    wait_s = time.perf_counter() - t0

    timed_out = len(pending)
    completed = counts["completed"]
    failed = counts["failed"]
    cancelled = counts["cancelled"]
    terminal = completed + failed + cancelled
    success_pct = (100.0 * completed / len(job_ids)) if job_ids else 0.0

    report = {
        "jobs_submitted": len(job_ids),
        "submit_errors": errors,
        "completed": completed,
        "failed": failed,
        "cancelled": cancelled,
        "timed_out_queued_or_running": timed_out,
        "success_rate_pct": round(success_pct, 2),
        "wall_clock_sec": round(wait_s, 2),
        "jobs_per_sec": round(terminal / wait_s, 2) if wait_s else 0,
        "worker_replicas_hint": args.workers_hint,
    }
    print(json.dumps(report, indent=2))

    # Resume-friendly one-liner
    print(
        f"\nRESULT: {len(job_ids)} jobs, ~{args.workers_hint} concurrent workers, "
        f"{success_pct:.1f}% completed successfully in {wait_s:.1f}s"
    )
    return 0 if timed_out == 0 and failed == 0 and errors == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
