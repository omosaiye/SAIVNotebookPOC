# Frozen Contracts (Session A)

This document freezes shared enum values and request/response payload shapes for US-001, US-002, and US-003.

## 1. Canonical enums

### File status
- `uploaded`
- `queued`
- `parsing`
- `OCR_fallback`
- `chunking`
- `embedding`
- `indexed`
- `failed`
- `deleting`
- `deleted`

### Pending upload-and-ask request status
- `waiting_for_index`
- `executing`
- `completed`
- `failed`
- `cancelled`

### Chat mode
- `grounded`

### Upload-and-ask scope
- `uploaded_files_only`
- `workspace`

## 2. Contract model source locations

- TypeScript enums and interfaces:
  - `packages/shared-types/src/enums.ts`
  - `packages/shared-types/src/contracts.ts`
- Canonical enum JSON:
  - `packages/shared-types/contracts/enums.json`
- Python enums and Pydantic models:
  - `services/shared/enums.py`
  - `services/shared/contracts.py`

## 3. Frozen payload shapes

### CitationResponse

```json
{
  "fileId": "file_123",
  "fileName": "vendor_contract.pdf",
  "page": 8,
  "sheetName": null,
  "sectionHeading": null,
  "snippet": "Net 30 days from invoice receipt...",
  "chunkId": "chunk_987",
  "score": 0.92
}
```

### FileSummary

```json
{
  "id": "file_123",
  "workspaceId": "ws_1",
  "fileName": "vendor_contract.pdf",
  "status": "uploaded",
  "uploadedAt": "2026-01-01T00:00:00Z"
}
```

### FileDetail

```json
{
  "id": "file_123",
  "workspaceId": "ws_1",
  "fileName": "vendor_contract.pdf",
  "status": "indexed",
  "uploadedAt": "2026-01-01T00:00:00Z",
  "mimeType": "application/pdf",
  "sizeBytes": 240122,
  "objectKey": "ws_1/file_123/vendor_contract.pdf",
  "parserUsed": "docling",
  "errorMessage": null
}
```

### UploadResponse

```json
{
  "fileId": "file_123",
  "status": "uploaded",
  "message": "File accepted for processing"
}
```

### ChatQueryRequest

```json
{
  "workspaceId": "ws_1",
  "chatSessionId": "chat_55",
  "mode": "grounded",
  "query": "What are the payment terms?",
  "scope": "workspace",
  "fileIds": ["file_123"]
}
```

### ChatQueryResponse

```json
{
  "requestId": "req_1",
  "status": "executing",
  "answer": null,
  "citations": [],
  "pendingRequestId": "pending_9"
}
```

### PendingUploadAndAskRequestState

```json
{
  "requestId": "pending_9",
  "workspaceId": "ws_1",
  "status": "waiting_for_index",
  "scope": "uploaded_files_only",
  "query": "Summarize this upload",
  "fileIds": ["file_123"],
  "createdAt": "2026-01-01T00:00:00Z",
  "updatedAt": "2026-01-01T00:00:00Z"
}
```

## 4. Route list and ownership status

Implemented by Session A:
- `GET /health` (API startup and configuration health)

Reserved contract routes for downstream sessions (shape frozen, behavior pending):
- `POST /api/v1/files/upload`
- `GET /api/v1/files`
- `GET /api/v1/files/{fileId}`
- `POST /api/v1/chat/query`
- `POST /api/v1/upload-and-ask`
- `GET /api/v1/upload-and-ask/{requestId}`

## 5. Lifecycle transitions

### File lifecycle
- `uploaded -> queued`
- `queued -> parsing`
- `parsing -> OCR_fallback`
- `parsing -> chunking`
- `OCR_fallback -> chunking`
- `chunking -> embedding`
- `embedding -> indexed`
- `* -> failed`
- `indexed -> deleting`
- `failed -> deleting`
- `deleting -> deleted`

### Upload-and-ask lifecycle
- `waiting_for_index -> executing`
- `executing -> completed`
- `executing -> failed`
- `waiting_for_index -> cancelled`
- `executing -> cancelled`

## 6. Freeze policy

Frozen in Session A:
- enum values
- request/response field names
- core lifecycle transitions

Extensible by later sessions:
- additive non-breaking fields
- additional read-only endpoints
- validation constraints that do not rename/remove frozen fields
