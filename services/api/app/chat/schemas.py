from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from services.shared.contracts import ChatQueryRequest, ChatQueryResponse, CitationResponse, ContractModel


class ChatMessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessageResponse(ContractModel):
    id: str
    session_id: str = Field(alias="sessionId")
    workspace_id: str = Field(alias="workspaceId")
    role: ChatMessageRole
    content: str
    created_at: datetime = Field(alias="createdAt")
    citations: list[CitationResponse] = Field(default_factory=list)


class ChatSessionCreateRequest(ContractModel):
    workspace_id: str = Field(alias="workspaceId")
    title: str | None = None


class ChatSessionResponse(ContractModel):
    id: str
    workspace_id: str = Field(alias="workspaceId")
    title: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class ChatSessionDetailResponse(ChatSessionResponse):
    messages: list[ChatMessageResponse] = Field(default_factory=list)


class ChatSessionListResponse(ContractModel):
    sessions: list[ChatSessionResponse]


class GroundedQueryRequest(ChatQueryRequest):
    """Alias wrapper to keep endpoint-scoped naming readable."""


class GroundedQueryResponse(ChatQueryResponse):
    error_code: str | None = Field(default=None, alias="errorCode")
    error_message: str | None = Field(default=None, alias="errorMessage")
