from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from services.shared.enums import ChatMode, FileStatus, PendingRequestStatus, UploadAndAskScope


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class CitationResponse(ContractModel):
    file_id: str = Field(alias="fileId")
    file_name: str = Field(alias="fileName")
    page: int | None = None
    sheet_name: str | None = Field(default=None, alias="sheetName")
    section_heading: str | None = Field(default=None, alias="sectionHeading")
    snippet: str
    chunk_id: str = Field(alias="chunkId")
    score: float


class FileSummary(ContractModel):
    id: str
    workspace_id: str = Field(alias="workspaceId")
    file_name: str = Field(alias="fileName")
    status: FileStatus
    uploaded_at: datetime = Field(alias="uploadedAt")


class FileDetail(FileSummary):
    mime_type: str = Field(alias="mimeType")
    size_bytes: int = Field(alias="sizeBytes", ge=0)
    object_key: str = Field(alias="objectKey")
    parser_used: str | None = Field(default=None, alias="parserUsed")
    error_message: str | None = Field(default=None, alias="errorMessage")


class UploadResponse(ContractModel):
    file_id: str = Field(alias="fileId")
    status: FileStatus
    message: str


class ChatQueryRequest(ContractModel):
    workspace_id: str = Field(alias="workspaceId")
    chat_session_id: str | None = Field(default=None, alias="chatSessionId")
    mode: ChatMode
    query: str
    scope: UploadAndAskScope
    file_ids: list[str] = Field(default_factory=list, alias="fileIds")


class ChatQueryResponse(ContractModel):
    request_id: str = Field(alias="requestId")
    status: PendingRequestStatus
    answer: str | None = None
    citations: list[CitationResponse] = Field(default_factory=list)
    pending_request_id: str | None = Field(default=None, alias="pendingRequestId")


class PendingUploadAndAskRequestState(ContractModel):
    request_id: str = Field(alias="requestId")
    workspace_id: str = Field(alias="workspaceId")
    status: PendingRequestStatus
    scope: UploadAndAskScope
    query: str
    file_ids: list[str] = Field(default_factory=list, alias="fileIds")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
