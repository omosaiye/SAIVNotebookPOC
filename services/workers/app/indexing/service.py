from __future__ import annotations

from services.shared.embedding import deterministic_embedding
from services.workers.app.models import ChunkHandoffRecord
from services.workers.app.persistence.repository import IngestionPersistenceRepository


class ChunkIndexingService:
    def __init__(
        self,
        *,
        repository: IngestionPersistenceRepository,
        embedding_model_name: str,
    ) -> None:
        self._repository = repository
        self._embedding_model_name = embedding_model_name

    def index_chunks(self, *, file_id: str, chunks: list[ChunkHandoffRecord]) -> int:
        embeddings_by_chunk_id = {
            chunk.chunk_id: {
                "model": self._embedding_model_name,
                "values": deterministic_embedding(chunk.text),
            }
            for chunk in chunks
        }
        self._repository.store_embeddings(
            file_id=file_id,
            embeddings_by_chunk_id=embeddings_by_chunk_id,
        )
        return len(embeddings_by_chunk_id)

