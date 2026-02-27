# Session E Indexing/Retrieval Storage

This implementation provides:

- Parsed document chunking with normalized text and stable chunk IDs.
- Embedding generation through the `EmbeddingProvider` abstraction.
- Qdrant vector write/search support via `QdrantVectorStore`.
- Persistent indexing run status and stored normalized chunk references in SQLite.

## Dependency notes

- `QdrantClientAdapter` is a clean integration boundary for the real `qdrant-client` package.
- If `qdrant-client` is unavailable, use `InMemoryQdrantClient` (test/dev fallback) until dependency wiring is complete.

## Flow

1. `IndexingPipeline.index_document` creates a run in `pending`, then marks `processing`.
2. `DocumentChunker` transforms `ParsedDocument` sections into normalized `ChunkRecord` objects.
3. `EmbeddingService` uses the configured provider to create `EmbeddingVector` rows.
4. `QdrantVectorStore` upserts vectors + retrieval metadata payloads.
5. `IndexingPersistence` stores chunk references and marks run `indexed`.
6. Any failure marks run `failed` with an error message.
