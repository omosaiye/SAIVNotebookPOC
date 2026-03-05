from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from services.api.app.auth.dependencies import reset_auth_dependencies
from services.api.app.chat.dependencies import reset_chat_dependencies
from services.api.app.files.dependencies import reset_file_dependencies
from services.api.app.main import create_app
from services.api.app.upload_and_ask.dependencies import reset_upload_and_ask_dependencies
from services.shared.config import load_api_settings


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
    monkeypatch.setenv("INGESTION_QUEUE_BACKEND", "in_memory")
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


def login(client: TestClient, *, email: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["accessToken"]


def test_login_and_profile(client: TestClient) -> None:
    token = login(client, email="owner@local.dev", password="dev-password")
    profile = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    payload = profile.json()
    assert payload["userId"] == "user_seed_owner"
    assert payload["workspaceIds"] == ["ws_1"]


def test_login_failure_records_audit_event(client: TestClient) -> None:
    failed = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@local.dev", "password": "bad-password"},
    )
    assert failed.status_code == 401

    token = login(client, email="owner@local.dev", password="dev-password")
    events = client.get(
        "/api/v1/auth/audit-events",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert events.status_code == 200
    actions = {item["action"] for item in events.json()}
    assert "auth_login_failed" in actions
    assert "auth_login_succeeded" in actions


def test_protected_routes_require_authentication(client: TestClient) -> None:
    denied = client.get("/api/v1/files", headers={"X-Workspace-Id": "ws_1"})
    assert denied.status_code == 401
    assert denied.json()["detail"] == "Missing authorization token"


def test_workspace_authorization_denies_cross_workspace_access(client: TestClient) -> None:
    token = login(client, email="owner@local.dev", password="dev-password")
    denied = client.get(
        "/api/v1/files",
        headers={"Authorization": f"Bearer {token}", "X-Workspace-Id": "ws_2"},
    )
    assert denied.status_code == 403
    assert denied.json()["detail"] == "Workspace access denied"


def test_file_upload_records_audit_event(client: TestClient) -> None:
    token = login(client, email="owner@local.dev", password="dev-password")
    upload = client.post(
        "/api/v1/files/upload",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Workspace-Id": "ws_1",
            "X-File-Name": "audit.txt",
            "Content-Type": "text/plain",
        },
        content=b"hello",
    )
    assert upload.status_code == 200

    events = client.get(
        "/api/v1/auth/audit-events",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert events.status_code == 200
    actions = {item["action"] for item in events.json()}
    assert "file_uploaded" in actions
