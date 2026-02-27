from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4


@dataclass
class IngestionJob:
    id: str
    file_id: str
    workspace_id: str
    enqueued_at: datetime


class IngestionQueue:
    def enqueue(self, *, file_id: str, workspace_id: str) -> IngestionJob:
        raise NotImplementedError


class InMemoryIngestionQueue(IngestionQueue):
    def __init__(self) -> None:
        self.jobs: list[IngestionJob] = []

    def enqueue(self, *, file_id: str, workspace_id: str) -> IngestionJob:
        job = IngestionJob(
            id=f"job_{uuid4().hex}",
            file_id=file_id,
            workspace_id=workspace_id,
            enqueued_at=datetime.now(tz=timezone.utc),
        )
        self.jobs.append(job)
        return job
