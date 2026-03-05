from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from services.api.app.auth.dependencies import reset_auth_dependencies
from services.api.app.files.dependencies import reset_file_dependencies
from services.api.app.main import create_app
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
    app = create_app()
    return TestClient(app)


def auth_header(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@local.dev", "password": "dev-password"},
    )
    assert response.status_code == 200
    token = response.json()["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def upload(
    client: TestClient,
    auth: dict[str, str],
    workspace_id: str,
    filename: str,
    body: bytes,
    content_type: str,
) -> dict:
    response = client.post(
        "/api/v1/files/upload",
        headers={
            **auth,
            "X-Workspace-Id": workspace_id,
            "X-File-Name": filename,
            "Content-Type": content_type,
        },
        content=body,
    )
    assert response.status_code == 200
    return response.json()


def test_upload_enqueues_and_can_be_listed(client: TestClient) -> None:
    auth = auth_header(client)
    payload = upload(client, auth, "ws_1", "report.pdf", b"%PDF-1.4 fake", "application/pdf")
    assert payload["status"] == "queued"

    list_response = client.get("/api/v1/files", headers={**auth, "X-Workspace-Id": "ws_1"})
    assert list_response.status_code == 200
    rows = list_response.json()
    assert len(rows) == 1
    assert rows[0]["status"] == "queued"


def test_upload_rejects_content_type_mismatch(client: TestClient) -> None:
    auth = auth_header(client)
    response = client.post(
        "/api/v1/files/upload",
        headers={
            **auth,
            "X-Workspace-Id": "ws_1",
            "X-File-Name": "report.pdf",
            "Content-Type": "text/plain",
        },
        content=b"%PDF-1.4 fake",
    )

    assert response.status_code == 400
    assert "Declared content type does not match" in response.json()["detail"]


def test_workspace_isolation_for_get_detail(client: TestClient) -> None:
    auth = auth_header(client)
    uploaded = upload(client, auth, "ws_1", "table.csv", b"a,b\n1,2", "text/csv")
    file_id = uploaded["fileId"]

    denied = client.get(f"/api/v1/files/{file_id}", headers={**auth, "X-Workspace-Id": "ws_2"})
    assert denied.status_code == 403


def test_filter_and_search(client: TestClient) -> None:
    auth = auth_header(client)
    upload(client, auth, "ws_1", "alpha.txt", b"hello", "text/plain")
    upload(client, auth, "ws_1", "bravo.txt", b"hello", "text/plain")

    search_response = client.get(
        "/api/v1/files",
        headers={**auth, "X-Workspace-Id": "ws_1"},
        params={"search": "bravo", "status": "queued"},
    )
    assert search_response.status_code == 200
    data = search_response.json()
    assert len(data) == 1
    assert data[0]["fileName"] == "bravo.txt"


def test_reprocess_and_delete(client: TestClient) -> None:
    auth = auth_header(client)
    uploaded = upload(client, auth, "ws_1", "photo.jpg", b"\xff\xd8\xffabc", "image/jpeg")
    file_id = uploaded["fileId"]

    reprocess = client.post(
        f"/api/v1/files/{file_id}/reprocess",
        headers={**auth, "X-Workspace-Id": "ws_1"},
    )
    assert reprocess.status_code == 200
    assert reprocess.json()["status"] == "queued"

    delete_response = client.delete(
        f"/api/v1/files/{file_id}",
        headers={**auth, "X-Workspace-Id": "ws_1"},
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"

    status = client.get(
        f"/api/v1/files/{file_id}/status",
        headers={**auth, "X-Workspace-Id": "ws_1"},
    )
    assert status.status_code == 200
    assert status.json()["status"] == "deleted"
