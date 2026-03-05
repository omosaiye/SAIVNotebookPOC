from __future__ import annotations

from fastapi import APIRouter, Depends

from services.api.app.auth.dependencies import get_workspace_access
from services.api.app.auth.models import WorkspaceAccessContext
from services.api.app.chat.dependencies import get_chat_service
from services.api.app.chat.models import (
    ChatSessionCreateRequest,
    ChatSessionDetail,
    ChatSessionSummary,
)
from services.api.app.chat.service import ChatService
from services.shared.contracts import ChatQueryRequest, ChatQueryResponse

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("/sessions", response_model=ChatSessionSummary)
def create_session(
    payload: ChatSessionCreateRequest,
    workspace_access: WorkspaceAccessContext = Depends(get_workspace_access),
    service: ChatService = Depends(get_chat_service),
) -> ChatSessionSummary:
    return service.create_session(
        workspace_access=workspace_access,
        title=payload.title,
    )


@router.get("/sessions", response_model=list[ChatSessionSummary])
def list_sessions(
    workspace_access: WorkspaceAccessContext = Depends(get_workspace_access),
    service: ChatService = Depends(get_chat_service),
) -> list[ChatSessionSummary]:
    return service.list_sessions(workspace_access=workspace_access)


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
def get_session(
    session_id: str,
    workspace_access: WorkspaceAccessContext = Depends(get_workspace_access),
    service: ChatService = Depends(get_chat_service),
) -> ChatSessionDetail:
    return service.get_session(workspace_access=workspace_access, session_id=session_id)


@router.post("/query", response_model=ChatQueryResponse)
def query(
    payload: ChatQueryRequest,
    workspace_access: WorkspaceAccessContext = Depends(get_workspace_access),
    service: ChatService = Depends(get_chat_service),
) -> ChatQueryResponse:
    return service.query(workspace_access=workspace_access, request=payload)

