from uuid import uuid4

from app.async_tasks import dispatch_background_task
from app.config import Config
from app.extensions import cache
try:
    from redis import Redis
except Exception:  # pragma: no cover
    Redis = None

try:
    from rq import Queue
except Exception:  # pragma: no cover
    Queue = None


class JobService:
    def __init__(self) -> None:
        self.redis_conn = None
        self.queue = None
        if Redis and Queue and Config.CACHE_REDIS_URL:
            try:
                self.redis_conn = Redis.from_url(Config.CACHE_REDIS_URL)
                self.queue = Queue("simpai_jobs", connection=self.redis_conn)
            except Exception:
                self.redis_conn = None
                self.queue = None

    def enqueue(self, fn, *args, **kwargs) -> str:
        job_id = f"job_{uuid4().hex[:16]}"
        cache.set(f"job:{job_id}", {"status": "queued"}, timeout=600)

        if self.queue:
            self.queue.enqueue(self._execute_job, job_id, fn, *args, **kwargs)
            return job_id

        def _runner():
            self._execute_job(job_id, fn, *args, **kwargs)

        dispatch_background_task(_runner)
        return job_id

    @staticmethod
    def _execute_job(job_id, fn, *args, **kwargs):
        try:
            result = fn(*args, **kwargs)
            cache.set(f"job:{job_id}", {"status": "done", "result": result}, timeout=600)
        except Exception as error:  # noqa: ANN001
            cache.set(
                f"job:{job_id}",
                {"status": "failed", "error": str(error)},
                timeout=600,
            )

    def get_status(self, job_id: str) -> dict:
        return cache.get(f"job:{job_id}") or {"status": "not_found"}
