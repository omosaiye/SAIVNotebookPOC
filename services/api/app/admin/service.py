from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock

from fastapi import HTTPException

from services.api.app.auth.audit import AuditService
from services.api.app.auth.models import AuditEventRecord
from services.api.app.admin.models import (
    AdminMetricsResponse,
    AdminSettingsPatchRequest,
    AdminSettingsResponse,
    IngestionJobRow,
    IngestionLogRow,
    IngestionStageTimingMetrics,
)
from services.api.app.files.models import ListFilesFilters
from services.api.app.files.queue import IngestionQueue
from services.api.app.files.repository import FileRepository
from services.shared.config import APISettings
from services.shared.enums import FileStatus


@dataclass
class RuntimeAdminSettings:
    llm_endpoint: str
    llm_model: str
    embedding_model_name: str
    chunk_size: int
    chunk_overlap: int
    max_file_size_mb: int


class AdminSettingsStore:
    def __init__(self, *, seed: APISettings) -> None:
        self._lock = Lock()
        self._settings = RuntimeAdminSettings(
            llm_endpoint=seed.llm_endpoint,
            llm_model=seed.llm_model,
            embedding_model_name=seed.embedding_model_name,
            chunk_size=seed.chunk_size,
            chunk_overlap=seed.chunk_overlap,
            max_file_size_mb=seed.max_file_size_mb,
        )

    def read(self) -> RuntimeAdminSettings:
        with self._lock:
            return RuntimeAdminSettings(**self._settings.__dict__)

    def update(self, patch: AdminSettingsPatchRequest) -> RuntimeAdminSettings:
        if not patch.has_updates():
            raise HTTPException(status_code=400, detail="At least one setting field is required")

        with self._lock:
            next_settings = RuntimeAdminSettings(**self._settings.__dict__)
            if patch.llm_endpoint is not None:
                next_settings.llm_endpoint = patch.llm_endpoint
            if patch.llm_model is not None:
                next_settings.llm_model = patch.llm_model
            if patch.embedding_model_name is not None:
                next_settings.embedding_model_name = patch.embedding_model_name
            if patch.chunk_size is not None:
                next_settings.chunk_size = patch.chunk_size
            if patch.chunk_overlap is not None:
                next_settings.chunk_overlap = patch.chunk_overlap
            if patch.max_file_size_mb is not None:
                next_settings.max_file_size_mb = patch.max_file_size_mb

            if next_settings.chunk_overlap >= next_settings.chunk_size:
                raise HTTPException(status_code=400, detail="chunkOverlap must be smaller than chunkSize")

            self._settings = next_settings
            return RuntimeAdminSettings(**self._settings.__dict__)


class AdminService:
    def __init__(
        self,
        *,
        settings_store: AdminSettingsStore,
        file_repository: FileRepository,
        ingestion_queue: IngestionQueue,
        audit_service: AuditService,
    ) -> None:
        self._settings_store = settings_store
        self._file_repository = file_repository
        self._ingestion_queue = ingestion_queue
        self._audit_service = audit_service

    def get_settings(self) -> AdminSettingsResponse:
        current = self._settings_store.read()
        return AdminSettingsResponse(
            llmEndpoint=current.llm_endpoint,
            llmModel=current.llm_model,
            embeddingModelName=current.embedding_model_name,
            chunkSize=current.chunk_size,
            chunkOverlap=current.chunk_overlap,
            maxFileSizeMb=current.max_file_size_mb,
        )

    def update_settings(self, patch: AdminSettingsPatchRequest) -> AdminSettingsResponse:
        current = self._settings_store.update(patch)
        return AdminSettingsResponse(
            llmEndpoint=current.llm_endpoint,
            llmModel=current.llm_model,
            embeddingModelName=current.embedding_model_name,
            chunkSize=current.chunk_size,
            chunkOverlap=current.chunk_overlap,
            maxFileSizeMb=current.max_file_size_mb,
        )

    def list_ingestion_jobs(
        self,
        *,
        workspace_id: str,
        include_deleted: bool,
        limit: int,
    ) -> list[IngestionJobRow]:
        files = self._file_repository.list(
            ListFilesFilters(
                workspace_id=workspace_id,
                include_deleted=include_deleted,
            )
        )
        audit_events = self._audit_service.list_events(workspace_id=workspace_id)
        latest_action_by_file: dict[str, AuditEventRecord] = {}
        for event in audit_events:
            if event.entity_type != "file" or not event.entity_id:
                continue
            latest_action_by_file.setdefault(event.entity_id, event)

        queue_job_by_file: dict[str, object] = {}
        for job in reversed(self._ingestion_queue.list_jobs()):
            if job.workspace_id == workspace_id:
                queue_job_by_file.setdefault(job.file_id, job)

        rows: list[IngestionJobRow] = []
        for file_record in files[:limit]:
            latest_action = latest_action_by_file.get(file_record.id)
            queue_job = queue_job_by_file.get(file_record.id)
            rows.append(
                IngestionJobRow(
                    fileId=file_record.id,
                    fileName=file_record.file_name,
                    status=file_record.status,
                    uploadedAt=file_record.uploaded_at,
                    queueJobId=getattr(queue_job, "id", None),
                    enqueuedAt=getattr(queue_job, "enqueued_at", None),
                    lastAction=latest_action.action if latest_action else None,
                    lastActionAt=latest_action.created_at if latest_action else None,
                    errorMessage=file_record.error_message,
                    retryEligible=file_record.status == FileStatus.FAILED,
                )
            )
        return rows

    def list_ingestion_logs(self, *, workspace_id: str, limit: int) -> list[IngestionLogRow]:
        events = self._audit_service.list_events(workspace_id=workspace_id)
        return [
            IngestionLogRow(
                id=event.id,
                action=event.action,
                entityType=event.entity_type,
                entityId=event.entity_id,
                createdAt=event.created_at,
                metadata=event.metadata,
            )
            for event in events[:limit]
        ]

    def get_metrics(self, *, workspace_id: str) -> AdminMetricsResponse:
        now = datetime.now(tz=timezone.utc)
        files = self._file_repository.list(
            ListFilesFilters(
                workspace_id=workspace_id,
                include_deleted=True,
            )
        )
        events = self._audit_service.list_events(workspace_id=workspace_id)

        status_counts: dict[str, int] = {}
        for row in files:
            key = row.status.value
            status_counts[key] = status_counts.get(key, 0) + 1

        queue_jobs = [
            job for job in self._ingestion_queue.list_jobs() if job.workspace_id == workspace_id
        ]
        queue_ages = [(now - job.enqueued_at).total_seconds() for job in queue_jobs]

        in_flight_statuses = {
            FileStatus.UPLOADED,
            FileStatus.QUEUED,
            FileStatus.PARSING,
            FileStatus.OCR_FALLBACK,
            FileStatus.CHUNKING,
            FileStatus.EMBEDDING,
            FileStatus.DELETING,
        }
        in_flight_ages = [
            (now - row.uploaded_at).total_seconds()
            for row in files
            if row.status in in_flight_statuses
        ]

        uploads_total = sum(1 for event in events if event.action == "file_uploaded")
        chat_query_count = sum(1 for event in events if event.action == "chat_query_executed")
        upload_and_ask_count = sum(1 for event in events if event.action == "upload_and_ask_requested")
        answer_events = [event for event in events if event.action == "answer_generated"]
        answers_generated_count = len(answer_events)
        answers_with_citations = sum(
            1 for event in answer_events if (event.metadata.get("citationCount") or 0) > 0
        )
        citation_percent = (
            (answers_with_citations / answers_generated_count) * 100.0
            if answers_generated_count
            else 0.0
        )

        return AdminMetricsResponse(
            statusCounts=status_counts,
            queueDepth=len(queue_jobs),
            uploadsTotal=uploads_total,
            chatQueryCount=chat_query_count,
            uploadAndAskCount=upload_and_ask_count,
            answersGeneratedCount=answers_generated_count,
            answersWithCitationsPercent=round(citation_percent, 2),
            stageTiming=IngestionStageTimingMetrics(
                avgQueueAgeSeconds=round(sum(queue_ages) / len(queue_ages), 2) if queue_ages else None,
                oldestQueueAgeSeconds=round(max(queue_ages), 2) if queue_ages else None,
                avgInFlightAgeSeconds=(
                    round(sum(in_flight_ages) / len(in_flight_ages), 2) if in_flight_ages else None
                ),
            ),
        )
