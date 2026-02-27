from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx
from fastapi import HTTPException, status

from services.shared.contracts import CitationResponse
from services.shared.enums import ChatMode, PendingRequestStatus

from .repository import ChunkRecord, InMemoryChatRepository, InMemoryChunkRepository
from .schemas import ChatMessageRole, GroundedQueryRequest, GroundedQueryResponse


class APIErrorCode:
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    MODE_NOT_SUPPORTED = "MODE_NOT_SUPPORTED"
    RETRIEVAL_EMPTY = "RETRIEVAL_EMPTY"
    LLM_BACKEND_ERROR = "LLM_BACKEND_ERROR"


@dataclass
class RetrievedChunk:
    chunk_id: str
    file_id: str
    file_name: str
    content: str
    score: float
    page: int | None = None
    sheet_name: str | None = None
    section_heading: str | None = None


class RetrievalService(Protocol):
    def retrieve(self, query: str, workspace_id: str, file_ids: list[str], top_k: int = 5) -> list[RetrievedChunk]: ...


class LLMService(Protocol):
    def complete(self, system_prompt: str, user_prompt: str) -> str: ...


class ScopedChunkRetrievalService:
    """Current retrieval implementation over local chunk persistence; swappable with Qdrant adapter."""

    def __init__(self, chunk_repo: InMemoryChunkRepository) -> None:
        self.chunk_repo = chunk_repo

    def retrieve(self, query: str, workspace_id: str, file_ids: list[str], top_k: int = 5) -> list[RetrievedChunk]:
        query_terms = {token.strip(".,?!").lower() for token in query.split() if token.strip()}
        chunks = self.chunk_repo.list_by_scope(workspace_id=workspace_id, file_ids=file_ids)

        scored: list[RetrievedChunk] = []
        for chunk in chunks:
            content_terms = {token.strip(".,?!").lower() for token in chunk.content.split() if token.strip()}
            overlap = len(query_terms.intersection(content_terms))
            if overlap <= 0:
                continue
            score = overlap / max(1, len(query_terms))
            scored.append(
                RetrievedChunk(
                    chunk_id=chunk.chunk_id,
                    file_id=chunk.file_id,
                    file_name=chunk.file_name,
                    content=chunk.content,
                    score=score,
                    page=chunk.page,
                    sheet_name=chunk.sheet_name,
                    section_heading=chunk.section_heading,
                )
            )

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]


class GroundedPromptBuilder:
    SYSTEM_PROMPT = (
        "You are a private enterprise assistant operating in strict grounded mode. "
        "Answer ONLY from provided context blocks. "
        "If context is insufficient, say you do not have enough grounded evidence. "
        "Cite supporting source ids in your reasoning. "
        "Do not invent file names, page numbers, or facts."
    )

    def build(self, query: str, chunks: list[RetrievedChunk]) -> tuple[str, str]:
        context_blocks: list[str] = []
        for index, chunk in enumerate(chunks, start=1):
            label = f"source_{index}"
            metadata = [f"file={chunk.file_name}", f"chunk={chunk.chunk_id}"]
            if chunk.page is not None:
                metadata.append(f"page={chunk.page}")
            if chunk.sheet_name:
                metadata.append(f"sheet={chunk.sheet_name}")
            if chunk.section_heading:
                metadata.append(f"section={chunk.section_heading}")
            context_blocks.append(f"[{label}] {'; '.join(metadata)}\n{chunk.content}")

        user_prompt = (
            "Question:\n"
            f"{query}\n\n"
            "Grounding Context:\n"
            + "\n\n".join(context_blocks)
        )
        return self.SYSTEM_PROMPT, user_prompt


class PrivateLLMAdapter:
    def __init__(self, endpoint: str, model: str, timeout_seconds: int = 20) -> None:
        self.endpoint = endpoint
        self.model = model
        self.timeout_seconds = timeout_seconds

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        }

        attempts = 2
        last_error: Exception | None = None
        for _ in range(attempts):
            try:
                response = httpx.post(self.endpoint, json=payload, timeout=self.timeout_seconds)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except (httpx.HTTPError, KeyError, IndexError) as exc:
                last_error = exc

        raise RuntimeError(f"llm_request_failed: {last_error}")


class GroundedQueryService:
    def __init__(
        self,
        chat_repo: InMemoryChatRepository,
        retrieval_service: RetrievalService,
        prompt_builder: GroundedPromptBuilder,
        llm_service: LLMService,
    ) -> None:
        self.chat_repo = chat_repo
        self.retrieval_service = retrieval_service
        self.prompt_builder = prompt_builder
        self.llm_service = llm_service

    def execute(self, request: GroundedQueryRequest) -> GroundedQueryResponse:
        if request.mode != ChatMode.GROUNDED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"errorCode": APIErrorCode.MODE_NOT_SUPPORTED, "message": "Only grounded mode is supported."},
            )

        session = self.chat_repo.get_session(request.chat_session_id or "", request.workspace_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"errorCode": APIErrorCode.SESSION_NOT_FOUND, "message": "Chat session not found in workspace."},
            )

        self.chat_repo.create_message(
            session_id=session.id,
            workspace_id=request.workspace_id,
            role=ChatMessageRole.USER,
            content=request.query,
        )

        chunks = self.retrieval_service.retrieve(
            query=request.query,
            workspace_id=request.workspace_id,
            file_ids=request.file_ids,
        )

        if not chunks:
            insufficiency = (
                "I do not have enough grounded evidence in the selected documents to answer that question."
            )
            assistant = self.chat_repo.create_message(
                session_id=session.id,
                workspace_id=request.workspace_id,
                role=ChatMessageRole.ASSISTANT,
                content=insufficiency,
            )
            return GroundedQueryResponse(
                requestId=assistant.id,
                status=PendingRequestStatus.COMPLETED,
                answer=insufficiency,
                citations=[],
                pendingRequestId=None,
                errorCode=APIErrorCode.RETRIEVAL_EMPTY,
                errorMessage="No matching grounded chunks were found for this query.",
            )

        system_prompt, user_prompt = self.prompt_builder.build(request.query, chunks)
        try:
            answer = self.llm_service.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={"errorCode": APIErrorCode.LLM_BACKEND_ERROR, "message": str(exc)},
            ) from exc

        assistant = self.chat_repo.create_message(
            session_id=session.id,
            workspace_id=request.workspace_id,
            role=ChatMessageRole.ASSISTANT,
            content=answer,
        )
        citations = build_citations(chunks)
        self.chat_repo.add_citations(message_id=assistant.id, citations=citations)

        return GroundedQueryResponse(
            requestId=assistant.id,
            status=PendingRequestStatus.COMPLETED,
            answer=answer,
            citations=citations,
            pendingRequestId=None,
        )


def build_citations(chunks: list[RetrievedChunk]) -> list[CitationResponse]:
    return [
        CitationResponse(
            fileId=chunk.file_id,
            fileName=chunk.file_name,
            page=chunk.page,
            sheetName=chunk.sheet_name,
            sectionHeading=chunk.section_heading,
            snippet=chunk.content[:280],
            chunkId=chunk.chunk_id,
            score=round(chunk.score, 4),
        )
        for chunk in chunks
    ]


def seed_chunks(chunk_repo: InMemoryChunkRepository) -> None:
    """Temporary local seed data to make retrieval behavior testable before indexing integration."""
    chunk_repo.upsert_chunks(
        [
            ChunkRecord(
                chunk_id="chunk_contract_terms",
                workspace_id="ws_demo",
                file_id="file_contract",
                file_name="vendor_contract.pdf",
                content="Payment terms are net 30 days from invoice receipt and late fees apply after 10 days.",
                page=8,
                section_heading="Payment Terms",
            ),
            ChunkRecord(
                chunk_id="chunk_security",
                workspace_id="ws_demo",
                file_id="file_security",
                file_name="security_policy.pdf",
                content="All vendor access must use multi-factor authentication and quarterly access reviews.",
                page=3,
                section_heading="Identity and Access",
            ),
            ChunkRecord(
                chunk_id="chunk_other_workspace",
                workspace_id="ws_other",
                file_id="file_other",
                file_name="other_workspace_notes.txt",
                content="Confidential details that should not leak across workspace boundaries.",
            ),
        ]
    )
