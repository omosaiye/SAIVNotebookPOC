# Worker Ingestion Pipeline (Session D)

Implemented stories:
- US-013 worker framework and orchestration skeleton
- US-014 docling-first parser service
- US-015 OCR fallback trigger and execution path
- US-016 structured CSV/XLSX extraction enhancements
- US-017 persistence of ingestion documents, chunks, and events in PostgreSQL

## Celery entrypoint contracts

Frozen enqueue contract consumed from Session C/API:
- task: `ingestion.process_file`
- kwargs:
  - `file_id`
  - `workspace_id`
  - `object_key`
  - `file_name`
  - `mime_type`
  - `size_bytes`
  - `correlation_id` (optional)

## Pipeline stages

1. Create/update `ingestion_documents` row (`queued`).
2. Transition to `parsing` and fetch source bytes from object storage.
3. Parse via `DoclingFirstParserService`.
4. Trigger OCR fallback when parse output is empty for image/PDF mime-types.
5. Persist parsed metadata and transition to `chunking`.
6. Persist normalized chunks to `ingestion_chunks`.
7. Emit `chunking_handoff_ready` event and return handoff payload for Session E.

## Persistence model

Tables created by worker bootstrap repository (`CREATE TABLE IF NOT EXISTS`):
- `ingestion_documents`
- `ingestion_chunks`
- `ingestion_events`

Chunk metadata persisted for downstream retrieval/indexing:
- `page`
- `sheet_name`
- `section_heading`
- `token_estimate`
- parser-specific metadata JSON

## Supported file types

Primary parser routing:
- `.csv` / `text/csv` -> structured row extraction
- `.xlsx` -> structured worksheet row extraction
- all others -> docling-first, then text fallback decode

OCR fallback targets:
- `application/pdf`
- `image/png`
- `image/jpeg`
- `image/tiff`

## Retry semantics

`ingestion.process_file` retries automatically for transient errors (`ConnectionError`, `TimeoutError`) up to 3 attempts with backoff.

## Integration notes

For Session E (chunking/embedding/indexing):
- consume returned handoff payload from `ingestion.process_file`
- rely on stable chunk keys: `{file_id}:chunk:{ordinal}`
- ingestion worker stops at `chunking` state intentionally

For Session G (upload-and-ask orchestration):
- poll or subscribe to `ingestion_events` for `chunking_handoff_ready`
- failures are logged as `ingestion_failed` with error details
