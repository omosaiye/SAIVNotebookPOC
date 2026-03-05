from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from celery import Celery


@dataclass
class IngestionJob:
    id: str
    file_id: str
    workspace_id: str
    object_key: str
    file_name: str
    mime_type: str
    size_bytes: int
    enqueued_at: datetime
    correlation_id: str | None = None
    task_id: str | None = None
    dispatch_error: str | None = None


class IngestionQueue:
    def enqueue(
        self,
        *,
        file_id: str,
        workspace_id: str,
        object_key: str,
        file_name: str,
        mime_type: str,
        size_bytes: int,
        correlation_id: str | None = None,
    ) -> IngestionJob:
        raise NotImplementedError

    def list_jobs(self) -> list[IngestionJob]:
        return []

    def clear(self) -> None:
        return None


class InMemoryIngestionQueue(IngestionQueue):
    def __init__(self) -> None:
        self.jobs: list[IngestionJob] = []

    def enqueue(
        self,
        *,
        file_id: str,
        workspace_id: str,
        object_key: str,
        file_name: str,
        mime_type: str,
        size_bytes: int,
        correlation_id: str | None = None,
    ) -> IngestionJob:
        job = IngestionJob(
            id=f"job_{uuid4().hex}",
            file_id=file_id,
            workspace_id=workspace_id,
            object_key=object_key,
            file_name=file_name,
            mime_type=mime_type,
            size_bytes=size_bytes,
            enqueued_at=datetime.now(tz=timezone.utc),
            correlation_id=correlation_id,
        )
        self.jobs.append(job)
        return job

    def list_jobs(self) -> list[IngestionJob]:
        return list(self.jobs)

    def clear(self) -> None:
        self.jobs.clear()


class CeleryDispatchingIngestionQueue(InMemoryIngestionQueue):
    def __init__(
        self,
        *,
        broker_url: str,
        queue_name: str,
        task_name: str = "ingestion.process_file",
        strict_dispatch: bool = False,
    ) -> None:
        super().__init__()
        self._task_name = task_name
        self._queue_name = queue_name
        self._strict_dispatch = strict_dispatch
        self._dispatcher = Celery(
            "private_llm_api_dispatcher",
            broker=broker_url,
            backend=broker_url,
        )
        self._dispatcher.conf.update(
            task_publish_retry=False,
            broker_connection_retry_on_startup=False,
        )

    def enqueue(
        self,
        *,
        file_id: str,
        workspace_id: str,
        object_key: str,
        file_name: str,
        mime_type: str,
        size_bytes: int,
        correlation_id: str | None = None,
    ) -> IngestionJob:
        job = super().enqueue(
            file_id=file_id,
            workspace_id=workspace_id,
            object_key=object_key,
            file_name=file_name,
            mime_type=mime_type,
            size_bytes=size_bytes,
            correlation_id=correlation_id,
        )
        try:
            task = self._dispatcher.send_task(
                self._task_name,
                kwargs={
                    "file_id": file_id,
                    "workspace_id": workspace_id,
                    "object_key": object_key,
                    "file_name": file_name,
                    "mime_type": mime_type,
                    "size_bytes": size_bytes,
                    "correlation_id": correlation_id,
                },
                queue=self._queue_name,
                retry=False,
            )
            self.jobs[-1] = IngestionJob(
                **{
                    **job.__dict__,
                    "task_id": task.id,
                }
            )
        except Exception as exc:
            if self._strict_dispatch:
                raise
            self.jobs[-1] = IngestionJob(
                **{
                    **job.__dict__,
                    "dispatch_error": str(exc),
                }
            )
        return self.jobs[-1]
