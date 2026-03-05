from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from services.shared.enums import FileStatus


class AdminSettingsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    llm_endpoint: str = Field(alias="llmEndpoint")
    llm_model: str = Field(alias="llmModel")
    embedding_model_name: str = Field(alias="embeddingModelName")
    chunk_size: int = Field(alias="chunkSize")
    chunk_overlap: int = Field(alias="chunkOverlap")
    max_file_size_mb: int = Field(alias="maxFileSizeMb")


class AdminSettingsPatchRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    llm_endpoint: str | None = Field(default=None, alias="llmEndpoint")
    llm_model: str | None = Field(default=None, alias="llmModel")
    embedding_model_name: str | None = Field(default=None, alias="embeddingModelName")
    chunk_size: int | None = Field(default=None, alias="chunkSize", ge=1)
    chunk_overlap: int | None = Field(default=None, alias="chunkOverlap", ge=0)
    max_file_size_mb: int | None = Field(default=None, alias="maxFileSizeMb", ge=1)

    def has_updates(self) -> bool:
        return any(
            value is not None
            for value in [
                self.llm_endpoint,
                self.llm_model,
                self.embedding_model_name,
                self.chunk_size,
                self.chunk_overlap,
                self.max_file_size_mb,
            ]
        )


class IngestionJobRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    file_id: str = Field(alias="fileId")
    file_name: str = Field(alias="fileName")
    status: FileStatus
    uploaded_at: datetime = Field(alias="uploadedAt")
    queue_job_id: str | None = Field(default=None, alias="queueJobId")
    enqueued_at: datetime | None = Field(default=None, alias="enqueuedAt")
    last_action: str | None = Field(default=None, alias="lastAction")
    last_action_at: datetime | None = Field(default=None, alias="lastActionAt")
    error_message: str | None = Field(default=None, alias="errorMessage")
    retry_eligible: bool = Field(alias="retryEligible")


class IngestionLogRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    action: str
    entity_type: str = Field(alias="entityType")
    entity_id: str | None = Field(default=None, alias="entityId")
    created_at: datetime = Field(alias="createdAt")
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestionStageTimingMetrics(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    avg_queue_age_seconds: float | None = Field(default=None, alias="avgQueueAgeSeconds")
    oldest_queue_age_seconds: float | None = Field(default=None, alias="oldestQueueAgeSeconds")
    avg_in_flight_age_seconds: float | None = Field(default=None, alias="avgInFlightAgeSeconds")


class AdminMetricsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status_counts: dict[str, int] = Field(default_factory=dict, alias="statusCounts")
    queue_depth: int = Field(alias="queueDepth")
    uploads_total: int = Field(alias="uploadsTotal")
    chat_query_count: int = Field(alias="chatQueryCount")
    upload_and_ask_count: int = Field(alias="uploadAndAskCount")
    answers_generated_count: int = Field(alias="answersGeneratedCount")
    answers_with_citations_percent: float = Field(alias="answersWithCitationsPercent")
    stage_timing: IngestionStageTimingMetrics = Field(alias="stageTiming")
