from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from services.shared.contracts import CitationResponse
from services.shared.enums import PendingRequestStatus, UploadAndAskScope


class PendingUploadAndAskRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    request_id: str = Field(alias="requestId")
    workspace_id: str = Field(alias="workspaceId")
    query: str
    scope: UploadAndAskScope
    file_ids: list[str] = Field(default_factory=list, alias="fileIds")
    status: PendingRequestStatus
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    answer: str | None = None
    citations: list[CitationResponse] = Field(default_factory=list)
    error_message: str | None = Field(default=None, alias="errorMessage")


class UploadAndAskCreateResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    request_id: str = Field(alias="requestId")
    status: PendingRequestStatus
    message: str


class UploadAndAskStatusResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    request_id: str = Field(alias="requestId")
    workspace_id: str = Field(alias="workspaceId")
    status: PendingRequestStatus
    scope: UploadAndAskScope
    query: str
    file_ids: list[str] = Field(default_factory=list, alias="fileIds")
    file_statuses: dict[str, str] = Field(default_factory=dict, alias="fileStatuses")
    answer: str | None = None
    citations: list[CitationResponse] = Field(default_factory=list)
    error_message: str | None = Field(default=None, alias="errorMessage")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
