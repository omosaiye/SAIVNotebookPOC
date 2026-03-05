from __future__ import annotations

from services.api.app.auth.dependencies import get_audit_service
from services.api.app.chat.llm_adapter import StubPrivateLLMAdapter
from services.api.app.chat.repository import InMemoryChatRepository
from services.api.app.chat.retrieval import FileBackedRetrievalService, PostgresIndexedRetrievalService
from services.api.app.chat.service import ChatService
from services.api.app.files.dependencies import get_file_repository
from services.api.app.upload_and_ask.chat_backend import (
    ChatServiceGroundedQueryExecutor,
    GroundedQueryExecutor,
)
from services.shared.config import load_api_settings

_CHAT_REPOSITORY = InMemoryChatRepository()
_LLM_ADAPTER = StubPrivateLLMAdapter()


def get_chat_service() -> ChatService:
    settings = load_api_settings()
    fallback = FileBackedRetrievalService(file_repository=get_file_repository())
    return ChatService(
        repository=_CHAT_REPOSITORY,
        retrieval_service=PostgresIndexedRetrievalService(
            database_url=settings.database_url,
            fallback=fallback,
        ),
        llm_adapter=_LLM_ADAPTER,
        audit_service=get_audit_service(),
    )


def get_grounded_query_executor() -> GroundedQueryExecutor:
    return ChatServiceGroundedQueryExecutor(chat_service=get_chat_service())


def reset_chat_dependencies() -> None:
    _CHAT_REPOSITORY.clear()
