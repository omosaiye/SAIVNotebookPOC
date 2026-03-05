from __future__ import annotations

from datetime import datetime
from threading import Lock

from services.api.app.chat.models import ChatMessageRecord, ChatSessionRecord


class InMemoryChatRepository:
    def __init__(self) -> None:
        self._sessions: dict[str, ChatSessionRecord] = {}
        self._messages: dict[str, list[ChatMessageRecord]] = {}
        self._lock = Lock()

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._messages.clear()

    def create_session(self, session: ChatSessionRecord) -> ChatSessionRecord:
        with self._lock:
            self._sessions[session.id] = session
            self._messages.setdefault(session.id, [])
        return session

    def get_session(self, session_id: str) -> ChatSessionRecord | None:
        return self._sessions.get(session_id)

    def list_sessions(self, *, workspace_id: str) -> list[ChatSessionRecord]:
        rows = [row for row in self._sessions.values() if row.workspace_id == workspace_id]
        return sorted(rows, key=lambda item: item.updated_at, reverse=True)

    def append_message(self, message: ChatMessageRecord) -> ChatMessageRecord:
        with self._lock:
            self._messages.setdefault(message.session_id, []).append(message)
        return message

    def list_messages(self, session_id: str) -> list[ChatMessageRecord]:
        rows = self._messages.get(session_id, [])
        return sorted(rows, key=lambda item: item.created_at)

    def touch_session(self, *, session_id: str, updated_at: datetime) -> ChatSessionRecord | None:
        with self._lock:
            row = self._sessions.get(session_id)
            if row is None:
                return None
            updated = row.model_copy(update={"updated_at": updated_at})
            self._sessions[session_id] = updated
            return updated

