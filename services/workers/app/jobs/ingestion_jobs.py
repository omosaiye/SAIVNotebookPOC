from __future__ import annotations

from celery import Task

from services.shared.config import load_worker_settings
from services.shared.enums import FileStatus
from services.workers.app.celery_app import celery_app
from services.workers.app.indexing.service import ChunkIndexingService
from services.workers.app.models import IngestionJob
from services.workers.app.orchestration.ingestion_service import (
    IngestionOrchestrationService,
    map_retryable_failure,
)
from services.workers.app.parsers.docling_service import DoclingFirstParserService
from services.workers.app.parsers.ocr_service import OCRService
from services.workers.app.persistence.repository import IngestionPersistenceRepository
from services.workers.app.storage.object_store import ObjectStoreClient


class BaseRetryableTask(Task):
    autoretry_for = (ConnectionError, TimeoutError)
    retry_kwargs = {"max_retries": 3, "countdown": 5}
    retry_backoff = True


@celery_app.task(bind=True, base=BaseRetryableTask, name="ingestion.process_file")
def process_file_ingestion(
    self: Task,
    *,
    file_id: str,
    workspace_id: str,
    object_key: str,
    file_name: str,
    mime_type: str,
    size_bytes: int,
    correlation_id: str | None = None,
) -> dict:
    settings = load_worker_settings()
    repository = IngestionPersistenceRepository(settings.database_url)
    service = IngestionOrchestrationService(
        repository=repository,
        parser=DoclingFirstParserService(),
        ocr_service=OCRService(),
        object_store=ObjectStoreClient(),
        indexer=ChunkIndexingService(
            repository=repository,
            embedding_model_name=settings.embedding_model_name,
        ),
    )

    job = IngestionJob(
        file_id=file_id,
        workspace_id=workspace_id,
        object_key=object_key,
        file_name=file_name,
        mime_type=mime_type,
        size_bytes=size_bytes,
        correlation_id=correlation_id,
    )

    try:
        return service.run(job)
    except Exception as exc:
        repository.update_document_status(file_id, status=FileStatus.FAILED, error_message=str(exc))
        repository.record_event(file_id, "ingestion_failed", {"error": str(exc)})
        if map_retryable_failure(exc):
            raise self.retry(exc=exc)
        raise
