from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChatSessionRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    workspace_id: str = Field(alias="workspaceId")
    created_by: str = Field(alias="createdBy")
    title: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class ChatMessageRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    session_id: str = Field(alias="sessionId")
    role: str
    content: str
    created_at: datetime = Field(alias="createdAt")


class ChatSessionCreateRequest(BaseModel):
    title: str | None = None


class ChatSessionSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    updated_at: datetime = Field(alias="updatedAt")


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    role: str
    content: str
    created_at: datetime = Field(alias="createdAt")


class ChatSessionDetail(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    workspace_id: str = Field(alias="workspaceId")
    messages: list[ChatMessageResponse] = Field(default_factory=list)
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

