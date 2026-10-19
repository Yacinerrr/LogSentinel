"""Background CSV jobs: upload returns immediately, work happens in a thread, client polls progress.

v1 limits (documented on purpose): job state lives in memory, so a server restart forgets running jobs;
result files live in jobs_dir and are deleted after jobs_ttl_s. Move to a DB table + worker if we scale out.
"""
import csv
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from app.security import csv_safe

log = logging.getLogger("logsentinel.jobs")
HEADER = ["source", "log_message", "target_label", "tier", "confidence"]


class JobsBusy(Exception):
    pass


@dataclass
class Job:
    id: str
    key_id: str
    total: int
    path: Path
    status: str = "queued"        # queued | running | done | failed
    processed: int = 0
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None

    @property
    def progress(self) -> float:
        return round(self.processed / self.total, 3) if self.total else 1.0


class JobManager:
    def __init__(self, run_items, jobs_dir: str, chunk_size: int, ttl_s: int, max_running: int):
        self.run_items, self.chunk_size, self.ttl_s, self.max_running = run_items, chunk_size, ttl_s, max_running
        self.dir = Path(jobs_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, items, key_id: str) -> Job:
        self._cleanup()
        with self._lock:
            running = sum(1 for j in self._jobs.values() if j.status in ("queued", "running"))
            if running >= self.max_running:
                raise JobsBusy()
            job_id = uuid.uuid4().hex            # unguessable
            job = Job(id=job_id, key_id=key_id, total=len(items), path=self.dir / f"{job_id}.csv")
            self._jobs[job_id] = job
        threading.Thread(target=self._work, args=(job, items), daemon=True).start()
        return job

    def get(self, job_id: str, key_id: str) -> Job | None:
        job = self._jobs.get(job_id)
        return job if job and job.key_id == key_id else None   # other keys get 404, not 403

    def _work(self, job: Job, items) -> None:
        job.status = "running"
        try:
            with open(job.path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(HEADER)
                for i in range(0, len(items), self.chunk_size):
                    for r in self.run_items(items[i:i + self.chunk_size]):
                        w.writerow([csv_safe(r.source), csv_safe(r.log_message), r.label, r.tier,
                                    round(r.confidence, 3)])
                    job.processed = min(i + self.chunk_size, len(items))
            job.status = "done"
        except Exception:
            log.exception("job failed", extra={"request_id": job.id})
            job.status, job.error = "failed", "internal error"   # never leak internals to the client
        finally:
            job.finished_at = time.time()

    def _cleanup(self) -> None:
        now = time.time()
        with self._lock:
            old = [j for j in self._jobs.values() if j.finished_at and now - j.finished_at > self.ttl_s]
            for j in old:
                j.path.unlink(missing_ok=True)
                del self._jobs[j.id]
