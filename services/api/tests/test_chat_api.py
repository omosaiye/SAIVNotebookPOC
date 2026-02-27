from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from services.api.app.chat import dependencies
from services.api.app.chat.dependencies import get_query_service
from services.api.app.chat.services import (
    GroundedPromptBuilder,
    GroundedQueryService,
    PrivateLLMAdapter,
    RetrievedChunk,
    ScopedChunkRetrievalService,
    build_citations,
)
from services.api.app.main import create_app
from services.shared.enums import ChatMode, UploadAndAskScope


class StubLLM:
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        assert "strict grounded mode" in system_prompt
        assert "Grounding Context" in user_prompt
        return "The contract states payment terms are net 30 days from invoice receipt."


def seed_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/private_llm")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("S3_ENDPOINT", "http://localhost:9000")
    monkeypatch.setenv("S3_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("S3_SECRET_KEY", "minioadmin")
    monkeypatch.setenv("S3_BUCKET", "private-llm-documents")
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    monkeypatch.setenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
    monkeypatch.setenv("LLM_ENDPOINT", "http://localhost:8080/v1/chat/completions")
    monkeypatch.setenv("LLM_MODEL", "private-llm-model")


def test_chat_session_lifecycle_and_query(monkeypatch: pytest.MonkeyPatch) -> None:
    seed_environment(monkeypatch)
    dependencies.get_chat_repository.cache_clear()
    dependencies.get_chunk_repository.cache_clear()
    dependencies.get_query_service.cache_clear()

    app = create_app()

    chat_repo = dependencies.get_chat_repository()
    chunk_repo = dependencies.get_chunk_repository()
    query_service = GroundedQueryService(
        chat_repo=chat_repo,
        retrieval_service=ScopedChunkRetrievalService(chunk_repo),
        prompt_builder=GroundedPromptBuilder(),
        llm_service=StubLLM(),
    )
    app.dependency_overrides[get_query_service] = lambda: query_service

    client = TestClient(app)

    create_response = client.post("/api/chat/sessions", json={"workspaceId": "ws_demo", "title": "Vendor Q&A"})
    assert create_response.status_code == 201
    session_id = create_response.json()["id"]

    query_response = client.post(
        "/api/chat/query",
        json={
            "workspaceId": "ws_demo",
            "chatSessionId": session_id,
            "mode": ChatMode.GROUNDED.value,
            "query": "What are the payment terms?",
            "scope": UploadAndAskScope.WORKSPACE.value,
            "fileIds": [],
        },
    )
    assert query_response.status_code == 200
    payload = query_response.json()
    assert payload["answer"]
    assert payload["citations"]
    assert payload["citations"][0]["chunkId"] == "chunk_contract_terms"

    session_response = client.get(f"/api/chat/sessions/{session_id}", params={"workspaceId": "ws_demo"})
    assert session_response.status_code == 200
    messages = session_response.json()["messages"]
    assert len(messages) == 2
    assert messages[1]["citations"][0]["fileName"] == "vendor_contract.pdf"


def test_query_with_file_scope_filters_results(monkeypatch: pytest.MonkeyPatch) -> None:
    seed_environment(monkeypatch)
    dependencies.get_chat_repository.cache_clear()
    dependencies.get_chunk_repository.cache_clear()

    app = create_app()

    chat_repo = dependencies.get_chat_repository()
    chunk_repo = dependencies.get_chunk_repository()
    query_service = GroundedQueryService(
        chat_repo=chat_repo,
        retrieval_service=ScopedChunkRetrievalService(chunk_repo),
        prompt_builder=GroundedPromptBuilder(),
        llm_service=StubLLM(),
    )
    app.dependency_overrides[get_query_service] = lambda: query_service

    client = TestClient(app)
    session_id = client.post("/api/chat/sessions", json={"workspaceId": "ws_demo"}).json()["id"]

    response = client.post(
        "/api/chat/query",
        json={
            "workspaceId": "ws_demo",
            "chatSessionId": session_id,
            "mode": ChatMode.GROUNDED.value,
            "query": "What are the payment terms?",
            "scope": UploadAndAskScope.UPLOADED_FILES_ONLY.value,
            "fileIds": ["file_security"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["citations"] == []
    assert body["errorCode"] == "RETRIEVAL_EMPTY"


def test_build_citations_keeps_canonical_shape() -> None:
    citations = build_citations(
        [
            RetrievedChunk(
                chunk_id="chunk_1",
                file_id="file_1",
                file_name="policy.pdf",
                content="A" * 500,
                score=0.91789,
                page=10,
            )
        ]
    )
    payload = citations[0].model_dump(by_alias=True)
    assert payload == {
        "fileId": "file_1",
        "fileName": "policy.pdf",
        "page": 10,
        "sheetName": None,
        "sectionHeading": None,
        "snippet": "A" * 280,
        "chunkId": "chunk_1",
        "score": 0.9179,
    }


def test_private_llm_adapter_raises_for_failed_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken_post(*args: object, **kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr("httpx.post", broken_post)
    adapter = PrivateLLMAdapter(endpoint="http://example.com", model="test")
    with pytest.raises(RuntimeError):
        adapter.complete("system", "user")
