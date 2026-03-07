from __future__ import annotations

import pytest
from pydantic import ValidationError

from services.shared.config import APISettings


def base_env() -> dict[str, str]:
    return {
        "DATABASE_URL": "postgresql://postgres:postgres@localhost:5432/private_llm",
        "REDIS_URL": "redis://localhost:6379/0",
        "S3_ENDPOINT": "http://localhost:9000",
        "S3_ACCESS_KEY": "minioadmin",
        "S3_SECRET_KEY": "minioadmin",
        "S3_BUCKET": "private-llm-documents",
        "QDRANT_URL": "http://localhost:6333",
        "EMBEDDING_MODEL_NAME": "sentence-transformers/all-MiniLM-L6-v2",
        "LLM_ENDPOINT": "http://localhost:8080/v1/chat/completions",
        "LLM_MODEL": "private-llm-model",
    }


def seed_env(monkeypatch: pytest.MonkeyPatch, env: dict[str, str]) -> None:
    for key, value in env.items():
        monkeypatch.setenv(key, value)


def test_missing_required_settings_fail_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    env = base_env()
    env.pop("DATABASE_URL")
    seed_env(monkeypatch, env)

    with pytest.raises(ValidationError):
        APISettings()


def test_valid_settings_load_successfully(monkeypatch: pytest.MonkeyPatch) -> None:
    seed_env(monkeypatch, base_env())
    settings = APISettings()

    assert settings.database_url.startswith("postgresql://")
    assert settings.chunk_size > settings.chunk_overlap
