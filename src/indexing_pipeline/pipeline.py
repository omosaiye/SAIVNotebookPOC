from __future__ import annotations

from .chunking import DocumentChunker
from .embedding import EmbeddingService
from .models import IndexingRun, IndexingStatus, ParsedDocument
from .persistence import IndexingPersistence
from .qdrant_store import QdrantVectorStore


class IndexingPipeline:
    def __init__(
        self,
        chunker: DocumentChunker,
        embedding_service: EmbeddingService,
        vector_store: QdrantVectorStore,
        persistence: IndexingPersistence,
    ) -> None:
        self._chunker = chunker
        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._persistence = persistence

    def index_document(self, document: ParsedDocument) -> IndexingRun:
        run = self._persistence.create_run(document_id=document.document_id, tenant_id=document.tenant_id)
        self._persistence.update_status(run.run_id, IndexingStatus.PROCESSING)
        try:
            chunks = self._chunker.chunk(document)
            embeddings = self._embedding_service.generate_embeddings(chunks)
            self._vector_store.write_vectors(chunks, embeddings)
            self._persistence.persist_chunks(run.run_id, chunks)
            return self._persistence.update_status(run.run_id, IndexingStatus.INDEXED)
        except Exception as exc:  # noqa: BLE001
            return self._persistence.update_status(run.run_id, IndexingStatus.FAILED, str(exc))

    def get_indexing_status(self, run_id: str) -> IndexingRun:
        return self._persistence.get_run(run_id)
