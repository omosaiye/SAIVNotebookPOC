from __future__ import annotations

from pathlib import Path

from services.api.app.auth.dependencies import get_audit_service
from services.api.app.files.queue import InMemoryIngestionQueue
from services.api.app.files.repository import InMemoryFileRepository
from services.api.app.files.service import FileService
from services.api.app.files.storage import LocalObjectStorage
from services.shared.config import load_api_settings

_FILE_REPOSITORY = InMemoryFileRepository()
_INGESTION_QUEUE = InMemoryIngestionQueue()
_STORAGE = LocalObjectStorage(base_path=Path(".local-object-storage"))


def get_file_repository() -> InMemoryFileRepository:
    return _FILE_REPOSITORY


def get_file_service() -> FileService:
    settings = load_api_settings()
    return FileService(
        repository=_FILE_REPOSITORY,
        storage=_STORAGE,
        ingestion_queue=_INGESTION_QUEUE,
        max_file_size_bytes=settings.max_file_size_mb * 1024 * 1024,
        audit_service=get_audit_service(),
    )


def reset_file_dependencies() -> None:
    _FILE_REPOSITORY._records.clear()  # noqa: SLF001
    _INGESTION_QUEUE.jobs.clear()
