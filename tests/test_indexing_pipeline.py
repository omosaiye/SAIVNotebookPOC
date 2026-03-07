import tempfile
import unittest

from indexing_pipeline.chunking import ChunkingConfig, DocumentChunker
from indexing_pipeline.embedding import DeterministicHashEmbeddingProvider, EmbeddingService
from indexing_pipeline.models import IndexingStatus, ParsedDocument, ParsedSection
from indexing_pipeline.persistence import IndexingPersistence
from indexing_pipeline.pipeline import IndexingPipeline
from indexing_pipeline.qdrant_store import InMemoryQdrantClient, QdrantVectorStore


class IndexingPipelineTest(unittest.TestCase):
    def _document(self) -> ParsedDocument:
        return ParsedDocument(
            document_id="doc-1",
            tenant_id="tenant-1",
            source_uri="s3://library/doc-1.pdf",
            title="Document 1",
            sections=(
                ParsedSection(text="Alpha " * 80, section_name="intro", start_page=1, end_page=1),
                ParsedSection(text="Beta " * 50, section_name="body", start_page=2, end_page=3),
            ),
            metadata={"library_id": "lib-1", "uploaded_by": "user-1"},
        )

    def test_full_indexing_flow_persists_and_indexes(self) -> None:
        with tempfile.NamedTemporaryFile() as tmp:
            persistence = IndexingPersistence(db_path=tmp.name)
            pipeline = IndexingPipeline(
                chunker=DocumentChunker(ChunkingConfig(max_chars=220, overlap_chars=40, min_chunk_chars=50)),
                embedding_service=EmbeddingService(DeterministicHashEmbeddingProvider(dimensions=16)),
                vector_store=QdrantVectorStore(InMemoryQdrantClient(), "tenant-1"),
                persistence=persistence,
            )

            run = pipeline.index_document(self._document())

            self.assertEqual(run.status, IndexingStatus.INDEXED)
            chunks = persistence.list_chunks_for_document("doc-1")
            self.assertGreaterEqual(len(chunks), 2)

    def test_failed_status_is_captured(self) -> None:
        class FailingEmbeddingProvider(DeterministicHashEmbeddingProvider):
            def embed(self, texts: list[str]) -> list[tuple[float, ...]]:
                raise RuntimeError("provider down")

        with tempfile.NamedTemporaryFile() as tmp:
            persistence = IndexingPersistence(db_path=tmp.name)
            pipeline = IndexingPipeline(
                chunker=DocumentChunker(),
                embedding_service=EmbeddingService(FailingEmbeddingProvider()),
                vector_store=QdrantVectorStore(InMemoryQdrantClient(), "tenant-1"),
                persistence=persistence,
            )

            run = pipeline.index_document(self._document())
            self.assertEqual(run.status, IndexingStatus.FAILED)
            self.assertIn("provider down", run.error_message or "")


if __name__ == "__main__":
    unittest.main()
