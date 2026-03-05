from __future__ import annotations

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseServiceSettings(BaseSettings):
    app_env: str = Field(default="development")
    database_url: str
    redis_url: str
    s3_endpoint: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str
    qdrant_url: str
    embedding_model_name: str
    llm_endpoint: str
    llm_model: str
    chunk_size: int = Field(default=1200, ge=1)
    chunk_overlap: int = Field(default=200, ge=0)
    max_file_size_mb: int = Field(default=50, ge=1)

    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    @model_validator(mode="after")
    def validate_chunking(self) -> "BaseServiceSettings":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        return self


class APISettings(BaseServiceSettings):
    service_name: str = "api"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    celery_queue: str = "default"
    ingestion_queue_backend: str = "celery"
    object_store_base_path: str = ".local-object-storage"
    auth_session_ttl_minutes: int = Field(default=480, ge=1)
    auth_seed_enabled: bool = True
    auth_seed_user_id: str = "user_seed_owner"
    auth_seed_email: str = "owner@local.dev"
    auth_seed_password: str = "dev-password"
    auth_seed_workspace_ids: str = "ws_1"


class WorkerSettings(BaseServiceSettings):
    service_name: str = "workers"
    celery_queue: str = "default"
    ingestion_max_retries: int = Field(default=3, ge=0)
    object_store_base_path: str = ".local-object-storage"


@lru_cache
def load_api_settings() -> APISettings:
    return APISettings()


@lru_cache
def load_worker_settings() -> WorkerSettings:
    return WorkerSettings()
