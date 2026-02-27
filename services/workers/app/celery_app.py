from __future__ import annotations

from celery import Celery

from services.shared.config import load_worker_settings

settings = load_worker_settings()

celery_app = Celery(
    "private_llm_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_default_queue=settings.celery_queue,
    task_track_started=True,
)


@celery_app.task(name="health.ping")
def ping() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}
