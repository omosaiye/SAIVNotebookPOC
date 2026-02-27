from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from .dependencies import get_chat_repository, get_query_service
from .repository import InMemoryChatRepository
from .schemas import (
    ChatMessageResponse,
    ChatSessionCreateRequest,
    ChatSessionDetailResponse,
    ChatSessionListResponse,
    ChatSessionResponse,
    GroundedQueryRequest,
    GroundedQueryResponse,
)
from .services import GroundedQueryService

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    request: ChatSessionCreateRequest,
    chat_repo: InMemoryChatRepository = Depends(get_chat_repository),
) -> ChatSessionResponse:
    session = chat_repo.create_session(workspace_id=request.workspace_id, title=request.title)
    return ChatSessionResponse(
        id=session.id,
        workspaceId=session.workspace_id,
        title=session.title,
        createdAt=session.created_at,
        updatedAt=session.updated_at,
    )


@router.get("/sessions", response_model=ChatSessionListResponse)
def list_sessions(
    workspace_id: str = Query(alias="workspaceId"),
    chat_repo: InMemoryChatRepository = Depends(get_chat_repository),
) -> ChatSessionListResponse:
    sessions = chat_repo.list_sessions(workspace_id)
    return ChatSessionListResponse(
        sessions=[
            ChatSessionResponse(
                id=session.id,
                workspaceId=session.workspace_id,
                title=session.title,
                createdAt=session.created_at,
                updatedAt=session.updated_at,
            )
            for session in sessions
        ]
    )


@router.get("/sessions/{session_id}", response_model=ChatSessionDetailResponse)
def get_session(
    session_id: str,
    workspace_id: str = Query(alias="workspaceId"),
    chat_repo: InMemoryChatRepository = Depends(get_chat_repository),
) -> ChatSessionDetailResponse:
    session = chat_repo.get_session(session_id=session_id, workspace_id=workspace_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    messages = chat_repo.list_messages(session_id=session_id, workspace_id=workspace_id)
    return ChatSessionDetailResponse(
        id=session.id,
        workspaceId=session.workspace_id,
        title=session.title,
        createdAt=session.created_at,
        updatedAt=session.updated_at,
        messages=[
            ChatMessageResponse(
                id=message.id,
                sessionId=message.session_id,
                workspaceId=message.workspace_id,
                role=message.role,
                content=message.content,
                createdAt=message.created_at,
                citations=chat_repo.list_citations(message.id),
            )
            for message in messages
        ],
    )


@router.post("/query", response_model=GroundedQueryResponse)
def query_chat(
    request: GroundedQueryRequest,
    query_service: GroundedQueryService = Depends(get_query_service),
) -> GroundedQueryResponse:
    return query_service.execute(request)
