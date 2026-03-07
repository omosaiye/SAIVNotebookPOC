from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException

from services.api.app.auth.audit import AuditService
from services.api.app.auth.models import WorkspaceAccessContext
from services.api.app.chat.llm_adapter import LLMAdapter
from services.api.app.chat.models import (
    ChatMessageRecord,
    ChatMessageResponse,
    ChatSessionDetail,
    ChatSessionRecord,
    ChatSessionSummary,
)
from services.api.app.chat.prompt_builder import build_grounded_prompt
from services.api.app.chat.repository import InMemoryChatRepository
from services.api.app.chat.retrieval import RetrievalService
from services.shared.contracts import ChatQueryRequest, ChatQueryResponse, CitationResponse
from services.shared.enums import ChatMode, PendingRequestStatus, UploadAndAskScope


class ChatService:
    def __init__(
        self,
        *,
        repository: InMemoryChatRepository,
        retrieval_service: RetrievalService,
        llm_adapter: LLMAdapter,
        audit_service: AuditService,
    ) -> None:
        self._repository = repository
        self._retrieval_service = retrieval_service
        self._llm_adapter = llm_adapter
        self._audit_service = audit_service

    def create_session(
        self,
        *,
        workspace_access: WorkspaceAccessContext,
        title: str | None,
    ) -> ChatSessionSummary:
        now = datetime.now(tz=timezone.utc)
        session = self._repository.create_session(
            ChatSessionRecord(
                id=f"sess_{uuid4().hex}",
                workspaceId=workspace_access.workspace_id,
                createdBy=workspace_access.user_id,
                title=(title or "New chat").strip() or "New chat",
                createdAt=now,
                updatedAt=now,
            )
        )
        return ChatSessionSummary(id=session.id, title=session.title, updatedAt=session.updated_at)

    def list_sessions(self, *, workspace_access: WorkspaceAccessContext) -> list[ChatSessionSummary]:
        rows = self._repository.list_sessions(workspace_id=workspace_access.workspace_id)
        return [
            ChatSessionSummary(id=row.id, title=row.title, updatedAt=row.updated_at)
            for row in rows
        ]

    def get_session(
        self,
        *,
        workspace_access: WorkspaceAccessContext,
        session_id: str,
    ) -> ChatSessionDetail:
        row = self._repository.get_session(session_id)
        if row is None or row.workspace_id != workspace_access.workspace_id:
            raise HTTPException(status_code=404, detail="Chat session not found")
        messages = self._repository.list_messages(session_id)
        return ChatSessionDetail(
            id=row.id,
            title=row.title,
            workspaceId=row.workspace_id,
            messages=[
                ChatMessageResponse(
                    id=item.id,
                    role=item.role,
                    content=item.content,
                    createdAt=item.created_at,
                )
                for item in messages
            ],
            createdAt=row.created_at,
            updatedAt=row.updated_at,
        )

    def query(
        self,
        *,
        workspace_access: WorkspaceAccessContext,
        request: ChatQueryRequest,
    ) -> ChatQueryResponse:
        if request.workspace_id != workspace_access.workspace_id:
            raise HTTPException(status_code=403, detail="Workspace access denied")
        if request.mode != ChatMode.GROUNDED:
            raise HTTPException(status_code=400, detail="Only grounded mode is supported")
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query is required")

        session_id = request.chat_session_id
        if session_id is None:
            session = self.create_session(
                workspace_access=workspace_access,
                title=request.query[:80],
            )
            session_id = session.id
        else:
            _ = self.get_session(
                workspace_access=workspace_access,
                session_id=session_id,
            )

        user_message = ChatMessageRecord(
            id=f"msg_{uuid4().hex}",
            sessionId=session_id,
            role="user",
            content=request.query,
            createdAt=datetime.now(tz=timezone.utc),
        )
        self._repository.append_message(user_message)

        answer_text, citations = self.generate_grounded_answer(
            workspace_id=workspace_access.workspace_id,
            actor_user_id=workspace_access.user_id,
            query=request.query,
            scope=request.scope,
            file_ids=request.file_ids,
        )

        assistant_message = ChatMessageRecord(
            id=f"msg_{uuid4().hex}",
            sessionId=session_id,
            role="assistant",
            content=answer_text,
            createdAt=datetime.now(tz=timezone.utc),
        )
        self._repository.append_message(assistant_message)
        self._repository.touch_session(
            session_id=session_id,
            updated_at=assistant_message.created_at,
        )

        return ChatQueryResponse(
            requestId=f"chatreq_{uuid4().hex}",
            status=PendingRequestStatus.COMPLETED,
            answer=answer_text,
            citations=citations,
            pendingRequestId=None,
        )

    def generate_grounded_answer(
        self,
        *,
        workspace_id: str,
        actor_user_id: str,
        query: str,
        scope: UploadAndAskScope,
        file_ids: list[str],
    ) -> tuple[str, list[CitationResponse]]:
        self._audit_service.record_event(
            action="chat_query_executed",
            entity_type="chat_query",
            actor_user_id=actor_user_id,
            workspace_id=workspace_id,
            metadata={"scope": scope.value, "fileCount": len(file_ids)},
        )

        chunks = self._retrieval_service.retrieve(
            workspace_id=workspace_id,
            query=query,
            scope=scope,
            file_ids=file_ids,
        )
        self._audit_service.record_event(
            action="chunks_retrieved",
            entity_type="chat_query",
            actor_user_id=actor_user_id,
            workspace_id=workspace_id,
            metadata={"chunkCount": len(chunks)},
        )

        prompt = build_grounded_prompt(query=query, chunks=chunks)
        answer = self._llm_adapter.generate(prompt=prompt).answer

        citations = [
            CitationResponse(
                fileId=chunk.file_id,
                fileName=chunk.file_name,
                page=chunk.page,
                sheetName=chunk.sheet_name,
                sectionHeading=chunk.section_heading,
                snippet=chunk.text,
                chunkId=chunk.chunk_id,
                score=chunk.score,
            )
            for chunk in chunks
        ]

        self._audit_service.record_event(
            action="answer_generated",
            entity_type="chat_query",
            actor_user_id=actor_user_id,
            workspace_id=workspace_id,
            metadata={"citationCount": len(citations)},
        )
        return answer, citations

