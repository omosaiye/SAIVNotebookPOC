from __future__ import annotations

from dataclasses import dataclass

from services.api.app.files.repository import InMemoryFileRepository
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
    def __init__(self, *, file_repository: InMemoryFileRepository) -> None:
        self._file_repository = file_repository

    def check(self, *, workspace_id: str, file_ids: list[str]) -> IndexReadiness:
        statuses: dict[str, FileStatus] = {}
        for file_id in file_ids:
            row = self._file_repository.get(file_id)
            if row is None or row.workspace_id != workspace_id:
                statuses[file_id] = FileStatus.FAILED
                continue
            statuses[file_id] = row.status
        return IndexReadiness(file_statuses=statuses)
