from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .models import ChunkRecord, EmbeddingVector, SearchResult


@dataclass(frozen=True)
class VectorPoint:
    id: str
    vector: tuple[float, ...]
    payload: dict[str, Any]


class QdrantClientProtocol(Protocol):
    def ensure_collection(self, collection_name: str, vector_size: int) -> None: ...

    def upsert(self, collection_name: str, points: list[VectorPoint]) -> None: ...

    def search(self, collection_name: str, vector: tuple[float, ...], top_k: int) -> list[tuple[str, float, dict[str, Any]]]: ...


class InMemoryQdrantClient(QdrantClientProtocol):
    def __init__(self) -> None:
        self._collections: dict[str, dict[str, VectorPoint]] = {}

    def ensure_collection(self, collection_name: str, vector_size: int) -> None:
        self._collections.setdefault(collection_name, {})

    def upsert(self, collection_name: str, points: list[VectorPoint]) -> None:
        coll = self._collections.setdefault(collection_name, {})
        for point in points:
            coll[point.id] = point

    def search(self, collection_name: str, vector: tuple[float, ...], top_k: int) -> list[tuple[str, float, dict[str, Any]]]:
        coll = self._collections.get(collection_name, {})
        scored: list[tuple[str, float, dict[str, Any]]] = []
        for point_id, point in coll.items():
            score = sum(a * b for a, b in zip(vector, point.vector))
            scored.append((point_id, score, point.payload))
        scored.sort(key=lambda row: row[1], reverse=True)
        return scored[:top_k]


class QdrantVectorStore:
    def __init__(self, client: QdrantClientProtocol, collection_name: str) -> None:
        self._client = client
        self._collection_name = collection_name

    def write_vectors(self, chunks: list[ChunkRecord], embeddings: list[EmbeddingVector]) -> None:
        if not embeddings:
            return

        vector_size = len(embeddings[0].values)
        self._client.ensure_collection(self._collection_name, vector_size)

        chunk_by_id = {chunk.chunk_id: chunk for chunk in chunks}
        points: list[VectorPoint] = []
        for embedding in embeddings:
            chunk = chunk_by_id[embedding.chunk_id]
            payload = {
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "tenant_id": chunk.tenant_id,
                "ordinal": chunk.ordinal,
                "text": chunk.text,
                "metadata": dict(chunk.metadata),
                "embedding_model": embedding.model_name,
            }
            points.append(VectorPoint(id=chunk.chunk_id, vector=embedding.values, payload=payload))

        self._client.upsert(self._collection_name, points)

    def search(self, query_vector: tuple[float, ...], top_k: int = 5) -> list[SearchResult]:
        matches = self._client.search(self._collection_name, query_vector, top_k)
        return [
            SearchResult(
                chunk_id=point_id,
                score=score,
                document_id=payload["document_id"],
                tenant_id=payload["tenant_id"],
                text=payload["text"],
                metadata=payload["metadata"],
            )
            for point_id, score, payload in matches
        ]


class QdrantClientAdapter(QdrantClientProtocol):
    """Adapter for real qdrant-client dependency; intentionally optional."""

    def __init__(self, endpoint: str, api_key: str | None = None) -> None:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, PointStruct, VectorParams
        except ImportError as exc:
            raise RuntimeError("qdrant-client is not installed; use InMemoryQdrantClient or install dependency") from exc

        self._distance = Distance
        self._point_struct = PointStruct
        self._vector_params = VectorParams
        self._client = QdrantClient(url=endpoint, api_key=api_key)

    def ensure_collection(self, collection_name: str, vector_size: int) -> None:
        existing = [collection.name for collection in self._client.get_collections().collections]
        if collection_name not in existing:
            self._client.create_collection(
                collection_name=collection_name,
                vectors_config=self._vector_params(size=vector_size, distance=self._distance.COSINE),
            )

    def upsert(self, collection_name: str, points: list[VectorPoint]) -> None:
        self._client.upsert(
            collection_name=collection_name,
            points=[self._point_struct(id=point.id, vector=point.vector, payload=point.payload) for point in points],
        )

    def search(self, collection_name: str, vector: tuple[float, ...], top_k: int) -> list[tuple[str, float, dict[str, Any]]]:
        matches = self._client.search(collection_name=collection_name, query_vector=vector, limit=top_k)
        return [(str(hit.id), float(hit.score), dict(hit.payload or {})) for hit in matches]
