from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from services.api.app.auth.dependencies import reset_auth_dependencies
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


def test_create_upload_and_ask_request(client: TestClient) -> None:
    auth = auth_header(client)
    response = client.post(
        "/api/v1/upload-and-ask",
        headers={**auth, "X-Workspace-Id": "ws_1"},
        data={"query": "Summarize this upload"},
        files=[("files", ("doc.txt", b"hello", "text/plain"))],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "waiting_for_index"

    status = client.get(
        f"/api/v1/upload-and-ask/{payload['requestId']}",
        headers={**auth, "X-Workspace-Id": "ws_1"},
    )
    assert status.status_code == 200
    state = status.json()
    assert state["scope"] == "uploaded_files_only"
    assert len(state["fileIds"]) == 1


def test_request_auto_executes_once_files_indexed(client: TestClient) -> None:
    auth = auth_header(client)
    created = client.post(
        "/api/v1/upload-and-ask",
        headers={**auth, "X-Workspace-Id": "ws_1"},
        data={"query": "What is in this file?"},
        files=[("files", ("doc.txt", b"hello", "text/plain"))],
    ).json()

    request_id = created["requestId"]
    waiting = client.get(
        f"/api/v1/upload-and-ask/{request_id}",
        headers={**auth, "X-Workspace-Id": "ws_1"},
    )
    assert waiting.status_code == 200
    waiting_payload = waiting.json()
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


def test_request_fails_if_required_file_is_deleted(client: TestClient) -> None:
    auth = auth_header(client)
    created = client.post(
        "/api/v1/upload-and-ask",
        headers={**auth, "X-Workspace-Id": "ws_1"},
        data={"query": "What changed?"},
        files=[("files", ("doc.txt", b"hello", "text/plain"))],
    ).json()

    request_id = created["requestId"]
    state = client.get(
        f"/api/v1/upload-and-ask/{request_id}",
        headers={**auth, "X-Workspace-Id": "ws_1"},
    ).json()
    file_id = state["fileIds"][0]

    delete_response = client.delete(
        f"/api/v1/files/{file_id}",
        headers={**auth, "X-Workspace-Id": "ws_1"},
    )
    assert delete_response.status_code == 200

    failed = client.get(
        f"/api/v1/upload-and-ask/{request_id}",
        headers={**auth, "X-Workspace-Id": "ws_1"},
    )
    assert failed.status_code == 200
    failed_payload = failed.json()
    assert failed_payload["status"] == "failed"
    assert "failed ingestion" in failed_payload["errorMessage"]
