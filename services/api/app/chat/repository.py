from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from services.shared.contracts import CitationResponse

from .schemas import ChatMessageRole


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class CitationRecord:
    message_id: str
    citation: CitationResponse
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class ChunkRecord:
    chunk_id: str
    workspace_id: str
    file_id: str
    file_name: str
    content: str
    page: int | None = None
    sheet_name: str | None = None
    section_heading: str | None = None


@dataclass
class ChatMessageRecord:
    id: str
    session_id: str
    workspace_id: str
    role: ChatMessageRole
    content: str
    created_at: datetime


@dataclass
class ChatSessionRecord:
    id: str
    workspace_id: str
    title: str
    created_at: datetime
    updated_at: datetime


class InMemoryChatRepository:
    def __init__(self) -> None:
        self._lock = Lock()
        self._sessions: dict[str, ChatSessionRecord] = {}
        self._messages: dict[str, list[ChatMessageRecord]] = {}
        self._citations: dict[str, list[CitationRecord]] = {}

    def create_session(self, workspace_id: str, title: str | None) -> ChatSessionRecord:
        with self._lock:
            now = utcnow()
            session = ChatSessionRecord(
                id=f"chat_{uuid4().hex[:12]}",
                workspace_id=workspace_id,
                title=title or "New chat",
                created_at=now,
                updated_at=now,
            )
            self._sessions[session.id] = session
            self._messages[session.id] = []
            return session

    def list_sessions(self, workspace_id: str) -> list[ChatSessionRecord]:
        sessions = [session for session in self._sessions.values() if session.workspace_id == workspace_id]
        return sorted(sessions, key=lambda s: s.updated_at, reverse=True)

    def get_session(self, session_id: str, workspace_id: str) -> ChatSessionRecord | None:
        session = self._sessions.get(session_id)
        if session is None or session.workspace_id != workspace_id:
            return None
        return session

    def create_message(
        self,
        session_id: str,
        workspace_id: str,
        role: ChatMessageRole,
        content: str,
    ) -> ChatMessageRecord:
        with self._lock:
            session = self.get_session(session_id=session_id, workspace_id=workspace_id)
            if session is None:
                raise KeyError("session_not_found")
            message = ChatMessageRecord(
                id=f"msg_{uuid4().hex[:12]}",
                session_id=session_id,
                workspace_id=workspace_id,
                role=role,
                content=content,
                created_at=utcnow(),
            )
            self._messages[session_id].append(message)
            session.updated_at = utcnow()
            return message

    def list_messages(self, session_id: str, workspace_id: str) -> list[ChatMessageRecord]:
        session = self.get_session(session_id=session_id, workspace_id=workspace_id)
        if session is None:
            return []
        return list(self._messages.get(session_id, []))

    def add_citations(self, message_id: str, citations: list[CitationResponse]) -> None:
        self._citations[message_id] = [CitationRecord(message_id=message_id, citation=c) for c in citations]

    def list_citations(self, message_id: str) -> list[CitationResponse]:
        return [record.citation for record in self._citations.get(message_id, [])]


class InMemoryChunkRepository:
    """Temporary retrieval backing store until indexing service integration is complete."""

    def __init__(self) -> None:
        self._chunks: dict[str, ChunkRecord] = {}

    def upsert_chunks(self, chunks: list[ChunkRecord]) -> None:
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk

    def list_by_scope(self, workspace_id: str, file_ids: list[str]) -> list[ChunkRecord]:
        candidates = [chunk for chunk in self._chunks.values() if chunk.workspace_id == workspace_id]
        if file_ids:
            candidates = [chunk for chunk in candidates if chunk.file_id in set(file_ids)]
        return candidates
