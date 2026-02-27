from __future__ import annotations

from dataclasses import dataclass

from services.shared.contracts import CitationResponse
from services.shared.enums import UploadAndAskScope


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
