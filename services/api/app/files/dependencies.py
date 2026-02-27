from __future__ import annotations

from pathlib import Path

from fastapi import Header, HTTPException

from services.api.app.files.queue import InMemoryIngestionQueue
from services.api.app.files.repository import InMemoryFileRepository
from services.api.app.files.service import FileService
from services.api.app.files.storage import LocalObjectStorage
from services.shared.config import load_api_settings

_FILE_REPOSITORY = InMemoryFileRepository()
_INGESTION_QUEUE = InMemoryIngestionQueue()
_STORAGE = LocalObjectStorage(base_path=Path(".local-object-storage"))


def get_file_service() -> FileService:
    settings = load_api_settings()
    return FileService(
        repository=_FILE_REPOSITORY,
        storage=_STORAGE,
        ingestion_queue=_INGESTION_QUEUE,
        max_file_size_bytes=settings.max_file_size_mb * 1024 * 1024,
    )


def get_workspace_id(x_workspace_id: str = Header(alias="X-Workspace-Id")) -> str:
    if not x_workspace_id:
        raise HTTPException(status_code=401, detail="Missing workspace authorization")
    return x_workspace_id


def reset_file_dependencies() -> None:
    _FILE_REPOSITORY._records.clear()  # noqa: SLF001
    _INGESTION_QUEUE.jobs.clear()
