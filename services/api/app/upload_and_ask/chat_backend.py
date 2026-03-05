from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from services.shared.contracts import CitationResponse
from services.shared.enums import UploadAndAskScope

if TYPE_CHECKING:
    from services.api.app.chat.service import ChatService


@dataclass
class GroundedAnswer:
    answer: str
    citations: list[CitationResponse]


class GroundedQueryExecutor:
    def ask(
        self,
        *,
        workspace_id: str,
        query: str,
        file_ids: list[str],
        scope: UploadAndAskScope,
    ) -> GroundedAnswer:
        raise NotImplementedError


class StubGroundedQueryExecutor(GroundedQueryExecutor):
    """Session G fallback while Session E/F integration finalizes."""

    def ask(
        self,
        *,
        workspace_id: str,
        query: str,
        file_ids: list[str],
        scope: UploadAndAskScope,
    ) -> GroundedAnswer:
        answer = (
            "Grounded answer generated for uploaded file set "
            f"({', '.join(file_ids)}) in workspace {workspace_id}. "
            f"Question: {query}"
        )
        return GroundedAnswer(answer=answer, citations=[])


class ChatServiceGroundedQueryExecutor(GroundedQueryExecutor):
    def __init__(self, *, chat_service: "ChatService") -> None:
        self._chat_service = chat_service

    def ask(
        self,
        *,
        workspace_id: str,
        query: str,
        file_ids: list[str],
        scope: UploadAndAskScope,
    ) -> GroundedAnswer:
        answer, citations = self._chat_service.generate_grounded_answer(
            workspace_id=workspace_id,
            actor_user_id="system_upload_and_ask",
            query=query,
            scope=scope,
            file_ids=file_ids,
        )
        return GroundedAnswer(answer=answer, citations=citations)
