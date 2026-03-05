from __future__ import annotations

from dataclasses import dataclass

import psycopg

from services.api.app.files.repository import FileRepository
from services.shared.enums import FileStatus


@dataclass
class IndexReadiness:
    file_statuses: dict[str, FileStatus]

    @property
    def all_indexed(self) -> bool:
        return all(status == FileStatus.INDEXED for status in self.file_statuses.values())

    @property
    def terminal_failure(self) -> bool:
        return any(status in {FileStatus.FAILED, FileStatus.DELETED} for status in self.file_statuses.values())


class IndexReadinessGateway:
    def check(self, *, workspace_id: str, file_ids: list[str]) -> IndexReadiness:
        raise NotImplementedError


class FileRepositoryIndexReadinessGateway(IndexReadinessGateway):
    def __init__(
        self,
        *,
        file_repository: FileRepository,
        database_url: str | None = None,
    ) -> None:
        self._file_repository = file_repository
        self._database_url = database_url

    def check(self, *, workspace_id: str, file_ids: list[str]) -> IndexReadiness:
        statuses: dict[str, FileStatus] = {}
        for file_id in file_ids:
            row = self._file_repository.get(file_id)
            if row is None or row.workspace_id != workspace_id:
                statuses[file_id] = FileStatus.FAILED
                continue
            statuses[file_id] = row.status

        db_statuses = self._read_db_statuses(workspace_id=workspace_id, file_ids=file_ids)
        for file_id, db_status in db_statuses.items():
            if db_status is not None:
                statuses[file_id] = db_status
        return IndexReadiness(file_statuses=statuses)

    def _read_db_statuses(
        self,
        *,
        workspace_id: str,
        file_ids: list[str],
    ) -> dict[str, FileStatus | None]:
        if not self._database_url or not file_ids:
            return {}

        try:
            with psycopg.connect(self._database_url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT file_id, status
                        FROM ingestion_documents
                        WHERE workspace_id = %s
                          AND file_id = ANY(%s)
                        """,
                        (workspace_id, file_ids),
                    )
                    rows = cursor.fetchall()
        except Exception:
            return {}

        result: dict[str, FileStatus | None] = {}
        for file_id, raw_status in rows:
            try:
                result[file_id] = FileStatus(raw_status)
            except ValueError:
                result[file_id] = None
        return result
