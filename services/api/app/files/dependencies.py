from __future__ import annotations

from pathlib import Path

from services.api.app.auth.dependencies import get_audit_service
from services.api.app.files.queue import (
    CeleryDispatchingIngestionQueue,
    InMemoryIngestionQueue,
    IngestionQueue,
)
from services.api.app.files.repository import InMemoryFileRepository
from services.api.app.files.service import FileService
from services.api.app.files.storage import LocalObjectStorage
from services.shared.config import load_api_settings

_FILE_REPOSITORY: InMemoryFileRepository | None = None
_INGESTION_QUEUE: IngestionQueue | None = None
_STORAGE: LocalObjectStorage | None = None


def _resolve_file_repository() -> InMemoryFileRepository:
    global _FILE_REPOSITORY
    if _FILE_REPOSITORY is None:
        settings = load_api_settings()
        _FILE_REPOSITORY = InMemoryFileRepository(database_url=settings.database_url)
    return _FILE_REPOSITORY


def _resolve_ingestion_queue() -> IngestionQueue:
    global _INGESTION_QUEUE
    if _INGESTION_QUEUE is None:
        settings = load_api_settings()
        if settings.ingestion_queue_backend == "in_memory":
            _INGESTION_QUEUE = InMemoryIngestionQueue()
        else:
            _INGESTION_QUEUE = CeleryDispatchingIngestionQueue(
                broker_url=settings.redis_url,
                queue_name=settings.celery_queue,
            )
    return _INGESTION_QUEUE


def _resolve_storage() -> LocalObjectStorage:
    global _STORAGE
    if _STORAGE is None:
        settings = load_api_settings()
        _STORAGE = LocalObjectStorage(base_path=Path(settings.object_store_base_path))
    return _STORAGE


def get_file_repository() -> InMemoryFileRepository:
    return _resolve_file_repository()


def get_ingestion_queue() -> IngestionQueue:
    return _resolve_ingestion_queue()


def get_file_service() -> FileService:
    settings = load_api_settings()
    return FileService(
        repository=_resolve_file_repository(),
        storage=_resolve_storage(),
        ingestion_queue=_resolve_ingestion_queue(),
        max_file_size_bytes=settings.max_file_size_mb * 1024 * 1024,
        audit_service=get_audit_service(),
    )


def reset_file_dependencies() -> None:
    global _FILE_REPOSITORY, _INGESTION_QUEUE, _STORAGE
    if _FILE_REPOSITORY is not None:
        _FILE_REPOSITORY.clear()
    if _INGESTION_QUEUE is not None:
        _INGESTION_QUEUE.clear()
    _FILE_REPOSITORY = None
    _INGESTION_QUEUE = None
    _STORAGE = None
