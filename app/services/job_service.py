from uuid import uuid4

from app.async_tasks import dispatch_background_task
from app.extensions import cache


class JobService:
    def enqueue(self, fn, *args, **kwargs) -> str:
        job_id = f"job_{uuid4().hex[:16]}"
        cache.set(f"job:{job_id}", {"status": "queued"}, timeout=600)

        def _runner():
            try:
                result = fn(*args, **kwargs)
                cache.set(f"job:{job_id}", {"status": "done", "result": result}, timeout=600)
            except Exception as error:  # noqa: ANN001
                cache.set(
                    f"job:{job_id}",
                    {"status": "failed", "error": str(error)},
                    timeout=600,
                )

        dispatch_background_task(_runner)
        return job_id

    def get_status(self, job_id: str) -> dict:
        return cache.get(f"job:{job_id}") or {"status": "not_found"}
