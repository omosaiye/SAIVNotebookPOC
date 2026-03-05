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


def test_admin_settings_read_and_patch(client: TestClient) -> None:
    auth = auth_header(client)
    get_response = client.get("/api/v1/admin/settings", headers={**auth, "X-Workspace-Id": "ws_1"})
    assert get_response.status_code == 200
    assert get_response.json()["chunkSize"] == 1200

    patch_response = client.patch(
        "/api/v1/admin/settings",
        headers={**auth, "X-Workspace-Id": "ws_1"},
        json={"chunkSize": 900, "chunkOverlap": 120},
    )
    assert patch_response.status_code == 200
    payload = patch_response.json()
    assert payload["chunkSize"] == 900
    assert payload["chunkOverlap"] == 120

    invalid = client.patch(
        "/api/v1/admin/settings",
        headers={**auth, "X-Workspace-Id": "ws_1"},
        json={"chunkSize": 400, "chunkOverlap": 600},
    )
    assert invalid.status_code == 400
    assert invalid.json()["detail"] == "chunkOverlap must be smaller than chunkSize"


def test_admin_jobs_logs_and_metrics(client: TestClient) -> None:
    auth = auth_header(client)
    uploaded = client.post(
        "/api/v1/files/upload",
        headers={
            **auth,
            "X-Workspace-Id": "ws_1",
            "X-File-Name": "metrics-source.txt",
            "Content-Type": "text/plain",
        },
        content=b"admin metrics source",
    )
    assert uploaded.status_code == 200
    file_id = uploaded.json()["fileId"]

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
            "query": "Summarize indexed file",
            "scope": "uploaded_files_only",
            "fileIds": [file_id],
        },
    )
    assert query.status_code == 200

    jobs = client.get("/api/v1/admin/ingestion-jobs", headers={**auth, "X-Workspace-Id": "ws_1"})
    assert jobs.status_code == 200
    jobs_payload = jobs.json()
    assert len(jobs_payload) >= 1
    assert jobs_payload[0]["fileId"] == file_id

    logs = client.get("/api/v1/admin/ingestion-logs", headers={**auth, "X-Workspace-Id": "ws_1"})
    assert logs.status_code == 200
    actions = [item["action"] for item in logs.json()]
    assert "file_uploaded" in actions
    assert "answer_generated" in actions

    metrics = client.get("/api/v1/admin/metrics", headers={**auth, "X-Workspace-Id": "ws_1"})
    assert metrics.status_code == 200
    payload = metrics.json()
    assert payload["queueDepth"] >= 1
    assert payload["uploadsTotal"] >= 1
    assert payload["chatQueryCount"] >= 1
    assert payload["answersGeneratedCount"] >= 1
    assert "indexed" in payload["statusCounts"]
