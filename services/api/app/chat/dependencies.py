from __future__ import annotations

from functools import lru_cache

from services.shared.config import load_api_settings

from .repository import InMemoryChatRepository, InMemoryChunkRepository
from .services import GroundedPromptBuilder, GroundedQueryService, PrivateLLMAdapter, ScopedChunkRetrievalService, seed_chunks


@lru_cache
def get_chat_repository() -> InMemoryChatRepository:
    return InMemoryChatRepository()


@lru_cache
def get_chunk_repository() -> InMemoryChunkRepository:
    repo = InMemoryChunkRepository()
    seed_chunks(repo)
    return repo


@lru_cache
def get_query_service() -> GroundedQueryService:
    settings = load_api_settings()
    chat_repo = get_chat_repository()
    retrieval = ScopedChunkRetrievalService(get_chunk_repository())
    prompt_builder = GroundedPromptBuilder()
    llm = PrivateLLMAdapter(endpoint=settings.llm_endpoint, model=settings.llm_model)
    return GroundedQueryService(chat_repo, retrieval, prompt_builder, llm)
