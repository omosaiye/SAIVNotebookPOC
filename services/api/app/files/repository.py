from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock

from services.api.app.files.models import FileRecord, ListFilesFilters
from services.shared.enums import FileStatus


class FileRepository:
    def create(self, record: FileRecord) -> FileRecord:
        raise NotImplementedError

    def get(self, file_id: str) -> FileRecord | None:
        raise NotImplementedError

    def update(self, record: FileRecord) -> FileRecord:
        raise NotImplementedError

    def list(self, filters: ListFilesFilters) -> list[FileRecord]:
        raise NotImplementedError


class InMemoryFileRepository(FileRepository):
    def __init__(self) -> None:
        self._records: dict[str, FileRecord] = {}
        self._lock = Lock()

    def create(self, record: FileRecord) -> FileRecord:
        with self._lock:
            self._records[record.id] = record
        return record

    def get(self, file_id: str) -> FileRecord | None:
        return self._records.get(file_id)

    def update(self, record: FileRecord) -> FileRecord:
        with self._lock:
            self._records[record.id] = record
        return record

    def list(self, filters: ListFilesFilters) -> list[FileRecord]:
        rows = [
            item for item in self._records.values() if item.workspace_id == filters.workspace_id
        ]
        if filters.status is not None:
            rows = [item for item in rows if item.status == filters.status]
        if filters.search:
            needle = filters.search.lower()
            rows = [item for item in rows if needle in item.file_name.lower()]
        if not filters.include_deleted:
            rows = [item for item in rows if item.status != FileStatus.DELETED]
        return sorted(rows, key=lambda item: item.uploaded_at, reverse=True)

    def transition_status(
        self,
        record: FileRecord,
        status: FileStatus,
        *,
        error_message: str | None = None,
    ) -> FileRecord:
        updated = record.model_copy(
            update={
                "status": status,
                "error_message": error_message,
                "deleted_at": (
                    datetime.now(tz=timezone.utc)
                    if status == FileStatus.DELETED
                    else record.deleted_at
                ),
            }
        )
        return self.update(updated)
