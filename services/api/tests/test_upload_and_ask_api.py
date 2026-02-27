from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

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


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    seed_environment(monkeypatch)
    load_api_settings.cache_clear()
    reset_file_dependencies()
    reset_upload_and_ask_dependencies()
    return TestClient(create_app())


def test_create_upload_and_ask_request(client: TestClient) -> None:
    response = client.post(
        "/api/v1/upload-and-ask",
        headers={"X-Workspace-Id": "ws_1"},
        data={"query": "Summarize this upload"},
        files=[("files", ("doc.txt", b"hello", "text/plain"))],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "waiting_for_index"

    status = client.get(
        f"/api/v1/upload-and-ask/{payload['requestId']}",
        headers={"X-Workspace-Id": "ws_1"},
    )
    assert status.status_code == 200
    state = status.json()
    assert state["scope"] == "uploaded_files_only"
    assert len(state["fileIds"]) == 1


def test_request_auto_executes_once_files_indexed(client: TestClient) -> None:
    created = client.post(
        "/api/v1/upload-and-ask",
        headers={"X-Workspace-Id": "ws_1"},
        data={"query": "What is in this file?"},
        files=[("files", ("doc.txt", b"hello", "text/plain"))],
    ).json()

    request_id = created["requestId"]
    waiting = client.get(f"/api/v1/upload-and-ask/{request_id}", headers={"X-Workspace-Id": "ws_1"})
    assert waiting.status_code == 200
    waiting_payload = waiting.json()
    file_id = waiting_payload["fileIds"][0]

    repository = get_file_repository()
    row = repository.get(file_id)
    assert row is not None
    repository.transition_status(row, FileStatus.INDEXED)

    completed = client.get(f"/api/v1/upload-and-ask/{request_id}", headers={"X-Workspace-Id": "ws_1"})
    assert completed.status_code == 200
    completed_payload = completed.json()
    assert completed_payload["status"] == "completed"
    assert completed_payload["answer"] is not None


def test_request_fails_if_required_file_is_deleted(client: TestClient) -> None:
    created = client.post(
        "/api/v1/upload-and-ask",
        headers={"X-Workspace-Id": "ws_1"},
        data={"query": "What changed?"},
        files=[("files", ("doc.txt", b"hello", "text/plain"))],
    ).json()

    request_id = created["requestId"]
    state = client.get(f"/api/v1/upload-and-ask/{request_id}", headers={"X-Workspace-Id": "ws_1"}).json()
    file_id = state["fileIds"][0]

    delete_response = client.delete(f"/api/v1/files/{file_id}", headers={"X-Workspace-Id": "ws_1"})
    assert delete_response.status_code == 200

    failed = client.get(f"/api/v1/upload-and-ask/{request_id}", headers={"X-Workspace-Id": "ws_1"})
    assert failed.status_code == 200
    failed_payload = failed.json()
    assert failed_payload["status"] == "failed"
    assert "failed ingestion" in failed_payload["errorMessage"]
