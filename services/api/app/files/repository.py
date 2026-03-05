from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock

import psycopg

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

    def refresh_workspace_statuses(self, workspace_id: str) -> None:
        return None

    def refresh_file_status(self, file_id: str) -> None:
        return None

    def clear(self) -> None:
        return None


class InMemoryFileRepository(FileRepository):
    def __init__(self, *, database_url: str | None = None) -> None:
        self._records: dict[str, FileRecord] = {}
        self._database_url = database_url
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
        self.refresh_workspace_statuses(filters.workspace_id)
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

    def refresh_workspace_statuses(self, workspace_id: str) -> None:
        if not self._database_url:
            return
        try:
            with psycopg.connect(self._database_url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT file_id, status, parser_used, error_message
                        FROM ingestion_documents
                        WHERE workspace_id = %s
                        """,
                        (workspace_id,),
                    )
                    rows = cursor.fetchall()
        except Exception:
            return

        with self._lock:
            for file_id, status_raw, parser_used, error_message in rows:
                record = self._records.get(file_id)
                if record is None:
                    continue
                if record.status in {FileStatus.DELETING, FileStatus.DELETED}:
                    continue
                try:
                    next_status = FileStatus(status_raw)
                except ValueError:
                    continue
                self._records[file_id] = record.model_copy(
                    update={
                        "status": next_status,
                        "parser_used": parser_used or record.parser_used,
                        "error_message": error_message,
                    }
                )

    def refresh_file_status(self, file_id: str) -> None:
        record = self.get(file_id)
        if record is None:
            return
        self.refresh_workspace_statuses(record.workspace_id)

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
