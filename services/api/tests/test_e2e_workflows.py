from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from services.api.app.admin.dependencies import reset_admin_dependencies
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
    reset_admin_dependencies()
    return TestClient(create_app())


def auth_header(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@local.dev", "password": "dev-password"},
    )
    assert response.status_code == 200
    token = response.json()["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def test_e2e_ingestion_then_grounded_query(client: TestClient) -> None:
    auth = auth_header(client)
    upload = client.post(
        "/api/v1/files/upload",
        headers={
            **auth,
            "X-Workspace-Id": "ws_1",
            "X-File-Name": "e2e-chat-source.txt",
            "Content-Type": "text/plain",
        },
        content=b"end to end source",
    )
    assert upload.status_code == 200
    file_id = upload.json()["fileId"]

    repository = get_file_repository()
    row = repository.get(file_id)
    assert row is not None
    repository.transition_status(row, FileStatus.INDEXED)

    query = client.post(
        "/api/v1/chat/query",
        headers={**auth, "X-Workspace-Id": "ws_1"},
        json={
            "workspaceId": "ws_1",
            "chatSessionId": None,
            "mode": "grounded",
            "query": "What is in the file?",
            "scope": "uploaded_files_only",
            "fileIds": [file_id],
        },
    )
    assert query.status_code == 200
    payload = query.json()
    assert payload["status"] == "completed"
    assert payload["answer"] is not None
    assert len(payload["citations"]) == 1
    assert payload["citations"][0]["fileId"] == file_id


def test_e2e_upload_and_ask_lifecycle(client: TestClient) -> None:
    auth = auth_header(client)
    created = client.post(
        "/api/v1/upload-and-ask",
        headers={**auth, "X-Workspace-Id": "ws_1"},
        data={"query": "Summarize this file"},
        files=[("files", ("e2e-upload-and-ask.txt", b"hello world", "text/plain"))],
    )
    assert created.status_code == 200
    request_id = created.json()["requestId"]

    waiting = client.get(
        f"/api/v1/upload-and-ask/{request_id}",
        headers={**auth, "X-Workspace-Id": "ws_1"},
    )
    assert waiting.status_code == 200
    waiting_payload = waiting.json()
    assert waiting_payload["status"] in {"waiting_for_index", "executing"}
    file_id = waiting_payload["fileIds"][0]

    repository = get_file_repository()
    row = repository.get(file_id)
    assert row is not None
    repository.transition_status(row, FileStatus.INDEXED)

    completed = client.get(
        f"/api/v1/upload-and-ask/{request_id}",
        headers={**auth, "X-Workspace-Id": "ws_1"},
    )
    assert completed.status_code == 200
    completed_payload = completed.json()
    assert completed_payload["status"] == "completed"
    assert completed_payload["answer"] is not None
