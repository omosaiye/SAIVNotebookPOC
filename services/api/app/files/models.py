from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from services.shared.enums import FileStatus


class FileRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    workspace_id: str
    file_name: str
    status: FileStatus
    uploaded_at: datetime
    mime_type: str
    size_bytes: int
    object_key: str
    parser_used: str | None = None
    error_message: str | None = None
    deleted_at: datetime | None = None


class ListFilesFilters(BaseModel):
    workspace_id: str
    status: FileStatus | None = None
    search: str | None = None
    include_deleted: bool = False


class UploadAccepted(BaseModel):
    file_id: str
    status: FileStatus
    message: str


class ReprocessRequest(BaseModel):
    workspace_id: str = Field(alias="workspaceId")


class FileListResponse(BaseModel):
    items: list[dict]
    total: int
