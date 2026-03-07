from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from services.api.app.auth.dependencies import reset_auth_dependencies
from services.api.app.chat.dependencies import reset_chat_dependencies
from services.api.app.files.dependencies import get_file_repository, reset_file_dependencies
from services.api.app.main import create_app
from services.api.app.upload_and_ask.dependencies import reset_upload_and_ask_dependencies
from services.shared.config import load_api_settings
from services.shared.enums import FileStatus


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
    monkeypatch.setenv("AUTH_SEED_ENABLED", "true")
    monkeypatch.setenv("AUTH_SEED_USER_ID", "user_seed_owner")
    monkeypatch.setenv("AUTH_SEED_EMAIL", "owner@local.dev")
    monkeypatch.setenv("AUTH_SEED_PASSWORD", "dev-password")
    monkeypatch.setenv("AUTH_SEED_WORKSPACE_IDS", "ws_1")


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    seed_environment(monkeypatch)
    load_api_settings.cache_clear()
    reset_auth_dependencies()
    reset_chat_dependencies()
    reset_file_dependencies()
    reset_upload_and_ask_dependencies()
    return TestClient(create_app())


def auth_header(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@local.dev", "password": "dev-password"},
    )
    assert response.status_code == 200
    token = response.json()["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def _upload_indexed_file(client: TestClient, auth: dict[str, str], workspace_id: str) -> str:
    uploaded = client.post(
        "/api/v1/files/upload",
        headers={
            **auth,
            "X-Workspace-Id": workspace_id,
            "X-File-Name": "chat-source.txt",
            "Content-Type": "text/plain",
        },
        content=b"context for chat",
    )
    assert uploaded.status_code == 200
    file_id = uploaded.json()["fileId"]

    repository = get_file_repository()
    row = repository.get(file_id)
    assert row is not None
    repository.transition_status(row, FileStatus.INDEXED)
    return file_id


def test_chat_session_crud(client: TestClient) -> None:
    auth = auth_header(client)
    created = client.post(
        "/api/v1/chat/sessions",
        headers={**auth, "X-Workspace-Id": "ws_1"},
        json={"title": "My Session"},
    )
    assert created.status_code == 200
    session_id = created.json()["id"]

    listed = client.get(
        "/api/v1/chat/sessions",
        headers={**auth, "X-Workspace-Id": "ws_1"},
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    detail = client.get(
        f"/api/v1/chat/sessions/{session_id}",
        headers={**auth, "X-Workspace-Id": "ws_1"},
    )
    assert detail.status_code == 200
    assert detail.json()["id"] == session_id


def test_chat_query_returns_answer_and_citations(client: TestClient) -> None:
    auth = auth_header(client)
    file_id = _upload_indexed_file(client, auth, "ws_1")

    response = client.post(
        "/api/v1/chat/query",
        headers={**auth, "X-Workspace-Id": "ws_1"},
        json={
            "workspaceId": "ws_1",
            "chatSessionId": None,
            "mode": "grounded",
            "query": "What is this about?",
            "scope": "uploaded_files_only",
            "fileIds": [file_id],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["answer"] is not None
    assert len(payload["citations"]) == 1
    assert payload["citations"][0]["fileId"] == file_id


def test_chat_query_requires_workspace_match(client: TestClient) -> None:
    auth = auth_header(client)
    response = client.post(
        "/api/v1/chat/query",
        headers={**auth, "X-Workspace-Id": "ws_1"},
        json={
            "workspaceId": "ws_2",
            "chatSessionId": None,
            "mode": "grounded",
            "query": "Mismatch",
            "scope": "workspace",
            "fileIds": [],
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Workspace access denied"

