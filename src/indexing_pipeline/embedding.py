from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod

from .models import ChunkRecord, EmbeddingVector


class EmbeddingProvider(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def embed(self, texts: list[str]) -> list[tuple[float, ...]]:
        raise NotImplementedError


class DeterministicHashEmbeddingProvider(EmbeddingProvider):
    """Offline provider for local development/tests when external provider is unavailable."""

    def __init__(self, dimensions: int = 32, model_name: str = "deterministic-hash-v1") -> None:
        self._dimensions = dimensions
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed(self, texts: list[str]) -> list[tuple[float, ...]]:
        vectors: list[tuple[float, ...]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            repeated = (digest * ((self._dimensions // len(digest)) + 1))[: self._dimensions]
            raw = [((byte / 255.0) * 2.0) - 1.0 for byte in repeated]
            norm = math.sqrt(sum(x * x for x in raw)) or 1.0
            vectors.append(tuple(x / norm for x in raw))
        return vectors


class EmbeddingService:
    def __init__(self, provider: EmbeddingProvider) -> None:
        self._provider = provider

    def generate_embeddings(self, chunks: list[ChunkRecord]) -> list[EmbeddingVector]:
        vectors = self._provider.embed([chunk.text for chunk in chunks])
        if len(vectors) != len(chunks):
            raise ValueError("Embedding provider returned mismatched vector count")

        return [
            EmbeddingVector(chunk_id=chunk.chunk_id, values=vector, model_name=self._provider.model_name)
            for chunk, vector in zip(chunks, vectors)
        ]
