from __future__ import annotations

from threading import Lock

from services.api.app.upload_and_ask.models import PendingUploadAndAskRecord


class PendingUploadAndAskRepository:
    def create(self, record: PendingUploadAndAskRecord) -> PendingUploadAndAskRecord:
        raise NotImplementedError

    def get(self, request_id: str) -> PendingUploadAndAskRecord | None:
        raise NotImplementedError

    def update(self, record: PendingUploadAndAskRecord) -> PendingUploadAndAskRecord:
        raise NotImplementedError


class InMemoryPendingUploadAndAskRepository(PendingUploadAndAskRepository):
    def __init__(self) -> None:
        self._records: dict[str, PendingUploadAndAskRecord] = {}
        self._lock = Lock()

    def create(self, record: PendingUploadAndAskRecord) -> PendingUploadAndAskRecord:
        with self._lock:
            self._records[record.request_id] = record
        return record

    def get(self, request_id: str) -> PendingUploadAndAskRecord | None:
        return self._records.get(request_id)

    def update(self, record: PendingUploadAndAskRecord) -> PendingUploadAndAskRecord:
        with self._lock:
            self._records[record.request_id] = record
        return record

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
