# Private LLM Workspace - Execution Backlog by User Story

## 1. Purpose

This document synthesizes the PRD into implementation-ready user stories for parallel Codex execution.

The goal is to let multiple independent coding sessions work in parallel with minimal collision. Each user story below is:
- scoped to a clear functional outcome
- independently testable and verifiable
- written so a competent junior engineer can implement it
- tied to explicit dependencies and handoff contracts

This backlog assumes the target stack from the PRD:
- **Frontend:** Next.js + TypeScript
- **Backend:** FastAPI + Pydantic + SQLAlchemy
- **Async jobs:** Celery + Redis
- **Storage:** PostgreSQL + S3-compatible object storage + Qdrant
- **Parsing:** Docling-first with specialist fallbacks
- **Embeddings:** sentence-transformers
- **Inference:** private LLM service via internal API

---

## 2. How to Use This with Parallel Codex Sessions

### Recommended execution model

Assign each Codex session one or more **user story groups** rather than isolated files.
Each session should own a coherent vertical slice with minimal overlap.

### Rules for all sessions

1. Do not change another session's API contract without updating this backlog and shared schemas.
2. Use shared response models and status enums where defined.
3. Prefer additive changes over refactors until integration phase.
4. Every completed story must include:
   - code
   - automated tests
   - local run instructions
   - verification notes
5. If a story depends on another story that is unfinished, the session should stub the dependency behind an interface and continue.

### Suggested parallel workstreams

| Workstream | Recommended Story Groups |
|---|---|
| Session A | Foundation + config + data model |
| Session B | Authentication + workspace membership |
| Session C | File upload + validation + object storage |
| Session D | Ingestion pipeline + parser orchestration |
| Session E | Chunking + embeddings + Qdrant indexing |
| Session F | Chat query + retrieval + prompt builder + citations |
| Session G | Upload-and-ask orchestration |
| Session H | Next.js document library + upload UX |
| Session I | Next.js chat UX + citation UX |
| Session J | Admin, observability, reprocess, delete, hardening |

---

## 3. Shared Contracts to Lock Before Coding

These are cross-cutting contracts. Every session must honor them.

### 3.1 Canonical file statuses

Use exactly these statuses unless the tech lead approves changes:
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

### 3.2 Canonical pending chat request statuses

Use exactly these statuses:
- `waiting_for_index`
- `executing`
- `completed`
- `failed`
- `cancelled`

### 3.3 Canonical chat modes

Use exactly these modes:
- `grounded`

### 3.4 Canonical upload-and-ask scopes

Use exactly these scopes:
- `uploaded_files_only`
- `workspace`

### 3.5 Minimum citation payload

Every grounded answer must be able to return citations in this shape:

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

### 3.6 Required metadata for each chunk

Every chunk must include:
- `chunk_id`
- `file_id`
- `document_id`
- `workspace_id`
- `source_type`
- `page_number` when available
- `sheet_name` when available
- `section_heading` when available
- `chunk_index`
- `token_count`
- `parser_used`
- `ocr_used`
- `content_hash`

---

## 4. Dependency Map

### Foundation dependencies
- Foundation stories unlock all other stories.

### Data flow dependencies
- Upload depends on auth, workspace model, and storage service.
- Ingestion depends on upload and data model.
- Chunking and embeddings depend on ingestion outputs.
- Chat retrieval depends on indexed chunks and workspace authorization.
- Upload-and-ask depends on upload, ingestion, and query execution.
- UI pages depend on the relevant APIs.

### Safe parallelization guidance

Can run in parallel early:
- frontend shell work
- backend auth/workspace work
- database model work
- service interface scaffolding
- mock API clients and UI state flows

Should converge before integration:
- exact schema names
- enum values
- response payload shapes
- event/status transitions

---

## 5. Epic Overview

1. Foundation and repository scaffolding
2. Authentication and workspace authorization
3. File upload and validation
4. Document library APIs and operations
5. Ingestion orchestration and parser pipeline
6. Chunking, embeddings, and vector indexing
7. Grounded query and citation generation
8. Upload-and-ask orchestration
9. Frontend workspace and library UX
10. Frontend chat and citations UX
11. Admin, observability, and reliability
12. End-to-end integration and golden corpus testing

---

# 6. User Stories by Epic

---

## Epic 1 - Foundation and Repository Scaffolding

### US-001 - Initialize monorepo structure and local developer environment

**User story**  
As an engineer, I want a working repository structure and local environment so every contributor can run the system consistently.

**Scope**
- Create directory structure aligned to PRD:
  - `apps/web`
  - `services/api`
  - `services/workers`
  - `packages/shared-types` if used
  - `infra/docker`
  - `docs/architecture`
- Add root README with local setup instructions.
- Add Docker Compose for PostgreSQL, Redis, MinIO, and Qdrant.
- Add `.env.example` files for web, api, and worker services.
- Add baseline lint/format commands.

**Dependencies**
- None

**Implementation notes**
- Keep startup simple and deterministic.
- Use one shared network in Docker Compose.
- Do not add production deployment complexity in this story.

**Acceptance criteria**
- A new developer can clone the repo, copy `.env.example`, start infrastructure, and run web/api/worker locally.
- Infrastructure containers start without manual edits.
- README documents exact commands.

**Verification**
- Run `docker compose up` successfully.
- Run web and API locally.
- Confirm Postgres, Redis, MinIO, and Qdrant are reachable.

**Tests**
- Basic health check script or smoke test for dependent services.

**Codex handoff output**
- repo scaffolding
- docker compose
- env templates
- root setup documentation

---

### US-002 - Create shared configuration system

**User story**  
As an engineer, I want centralized configuration so services behave consistently across environments.

**Scope**
- Add typed configuration loader for API and worker services.
- Support env vars from PRD:
  - database URL
  - redis URL
  - S3 settings
  - Qdrant URL
  - embedding model name
  - LLM endpoint and model
  - chunk size and overlap
  - max file size
- Add validation on startup.

**Dependencies**
- US-001

**Acceptance criteria**
- Invalid config fails fast at startup with a clear error.
- All required settings are accessible through one config module.

**Verification**
- Start API with missing required var and confirm failure.
- Start API with valid env and confirm config loads.

**Tests**
- Unit tests for config validation.

---

### US-003 - Define shared enums and schema contracts

**User story**  
As an engineer, I want canonical status enums and payload schemas so frontend and backend stay aligned.

**Scope**
- Define shared API response examples and status enums.
- Add backend Pydantic schemas for:
  - file summary
  - file detail
  - upload response
  - chat query request/response
  - citation response
  - pending upload-and-ask request state
- Add matching TypeScript types in frontend or generated equivalents.

**Dependencies**
- US-001, US-002

**Acceptance criteria**
- Shared statuses are defined once and reused.
- Frontend and backend compile using matching request/response shapes.

**Verification**
- Build frontend and backend with no schema mismatch errors.

**Tests**
- Schema serialization tests.

---

## Epic 2 - Authentication and Workspace Authorization

### US-004 - Implement baseline authentication flow

**User story**  
As a user, I want to sign in so the system can protect workspaces and documents.

**Scope**
- Implement baseline auth using email/password or chosen local auth path from the PRD.
- Create login endpoint and protected session handling.
- Add password hashing if local auth is used.
- Add protected frontend routes.

**Dependencies**
- US-001, US-002, US-003

**Out of scope**
- OIDC/SAML production SSO

**Acceptance criteria**
- Unauthenticated users cannot access workspace, file, chat, or admin pages.
- Authenticated users can sign in and maintain a valid session.

**Verification**
- Attempt protected route while logged out.
- Sign in successfully and reach dashboard.

**Tests**
- Unit tests for auth service.
- Integration tests for login success/failure.

---

### US-005 - Implement workspace membership and authorization checks

**User story**  
As a platform owner, I want workspace-scoped authorization so users only access their own files and chats.

**Scope**
- Create data model and services for:
  - workspaces
  - workspace members
  - roles
- Add authorization helper to validate workspace membership.
- Enforce authorization on file list, file detail, query, reprocess, delete, and chat session endpoints.

**Dependencies**
- US-004

**Acceptance criteria**
- A user cannot list or query resources outside their workspace.
- Authorized users can access workspace resources normally.

**Verification**
- Create two workspaces and two users.
- Confirm cross-workspace access is denied.

**Tests**
- Unit tests for membership checks.
- Integration tests for 403 cases.

---

### US-006 - Add audit event recording for security-relevant actions

**User story**  
As an auditor, I want important system actions logged so I can trace who did what.

**Scope**
- Add audit event model and service.
- Record at minimum:
  - file uploaded
  - file parsed
  - OCR fallback invoked
  - embeddings generated
  - chat query executed
  - chunks retrieved
  - answer generated
  - upload-and-ask lifecycle events
  - delete/reprocess actions

**Dependencies**
- US-005

**Acceptance criteria**
- Every major action persists an audit row with timestamp and metadata.

**Verification**
- Perform upload and query flow.
- Confirm audit rows exist.

**Tests**
- Unit tests for audit service.

---

## Epic 3 - File Upload and Validation

### US-007 - Implement file upload API with async enqueue behavior

**User story**  
As a knowledge user, I want to upload one or more files so they can be ingested asynchronously without blocking the UI.

**Scope**
- Create `POST /api/files`.
- Accept one or more files.
- Persist raw file to object storage.
- Create file records and ingestion job records.
- Enqueue parse job.
- Return quickly with file IDs and initial status.

**Dependencies**
- US-003, US-005

**Acceptance criteria**
- Upload request does not wait for parsing/indexing.
- File record is created with workspace association.
- Ingestion job is queued.

**Verification**
- Upload a PDF and confirm 202-like success behavior and queued status.
- Confirm file exists in object storage.

**Tests**
- Integration test for upload endpoint.
- Mocked object storage test.

---

### US-008 - Implement file type validation and signature detection

**User story**  
As a platform owner, I want strong file validation so unsupported or risky uploads are rejected early.

**Scope**
- Validate file size.
- Validate file extension.
- Validate MIME type.
- Validate file signature where possible.
- Reject password-protected/encrypted files in v1 with clear error.
- Quarantine or mark invalid uploads as failed.

**Dependencies**
- US-007

**Acceptance criteria**
- Invalid file types are rejected with explicit reason.
- Encrypted files are rejected cleanly.
- Signature mismatch is detected.

**Verification**
- Upload fake PDF renamed from another format.
- Upload oversize file.
- Upload encrypted PDF.

**Tests**
- Unit tests for validator.
- Integration tests for rejection cases.

---

### US-009 - Implement upload status tracking and ingestion job states

**User story**  
As a user, I want file processing states so I know whether my document is ready to query.

**Scope**
- Add file status transitions.
- Add ingestion job records with timestamps and errors.
- Implement `GET /api/files/{fileId}` returning status and latest job state.

**Dependencies**
- US-007

**Acceptance criteria**
- File records move through allowed statuses.
- Failed files carry visible error information.

**Verification**
- Upload file and observe state changes through processing.

**Tests**
- Unit tests for status transition helpers.

---

## Epic 4 - Document Library APIs and Operations

### US-010 - Implement file listing and filtering API

**User story**  
As a knowledge user, I want to browse files in my workspace so I can inspect ingestion progress and available sources.

**Scope**
- Create `GET /api/files`.
- Support filter params for:
  - status
  - type
  - owner
  - upload date
- Return paginated or bounded result set.

**Dependencies**
- US-005, US-009

**Acceptance criteria**
- Users can list only their workspace files.
- Filters return correct subsets.

**Verification**
- Seed files across statuses and test filters.

**Tests**
- API integration tests for filtering.

---

### US-011 - Implement file reprocess API and clean replacement behavior

**User story**  
As a user, I want to reprocess a file so I can recover from parsing issues or refresh indexing after pipeline changes.

**Scope**
- Create `POST /api/files/{fileId}/reprocess`.
- Queue reprocessing.
- Replace prior chunks and vectors cleanly.
- Preserve file identity and audit trail.

**Dependencies**
- US-009, US-017, US-018

**Acceptance criteria**
- Reprocess creates fresh chunks and vectors.
- Stale vectors are removed.
- File returns to active indexed state if successful.

**Verification**
- Reprocess a known file and verify chunk/version replacement.

**Tests**
- Integration test for reprocess lifecycle.

---

### US-012 - Implement file delete API with tombstone/cleanup behavior

**User story**  
As a user, I want to delete a file so it no longer appears in results and its artifacts are removed.

**Scope**
- Create `DELETE /api/files/{fileId}`.
- Delete or tombstone:
  - raw object
  - normalized artifacts
  - chunk rows
  - vectors
  - unresolved pending chat requests that require the file
- Write audit events.

**Dependencies**
- US-017, US-018, US-022

**Acceptance criteria**
- Deleted file cannot be retrieved or queried.
- Its vectors are removed from Qdrant.
- Pending upload-and-ask requests depending on it fail cleanly.

**Verification**
- Query before delete and after delete.
- Confirm no retrieval hits remain.

**Tests**
- Integration test for delete and vector removal.

---

## Epic 5 - Ingestion Orchestration and Parser Pipeline

### US-013 - Implement worker framework and job orchestration skeleton

**User story**  
As an engineer, I want a worker orchestration framework so ingestion stages run asynchronously and reliably.

**Scope**
- Set up Celery worker service.
- Register job types:
  - `parse_file`
  - `ocr_fallback`
  - `normalize_document`
  - `chunk_document`
  - `embed_chunks`
  - `index_vectors`
  - `delete_vectors`
  - `reprocess_file`
  - `execute_pending_chat_request`
- Add retryable task base.

**Dependencies**
- US-001, US-002

**Acceptance criteria**
- Worker can receive and execute tasks.
- Failed tasks can retry.

**Verification**
- Enqueue test task and confirm worker execution.

**Tests**
- Worker unit tests or task execution smoke tests.

---

### US-014 - Implement Docling-first parser service

**User story**  
As a system, I want a primary parser service so common file types can be normalized into reusable text artifacts.

**Scope**
- Implement parser selection logic.
- Parse at minimum:
  - PDF
  - DOCX
  - XLSX
  - CSV
  - PNG
  - JPEG
  - TXT
  - MD
- Persist normalized Markdown and JSON artifacts to object storage.
- Save parser metadata to database.

**Dependencies**
- US-013

**Acceptance criteria**
- Supported file types produce normalized output or a clear failure.
- Artifacts are stored with retrievable keys.

**Verification**
- Run parser against one file of each supported type.

**Tests**
- Unit tests for parser selection.
- Golden fixture tests for successful normalization.

---

### US-015 - Implement OCR fallback trigger and execution path

**User story**  
As a system, I want OCR fallback for scanned or image-heavy documents so low-text files remain searchable.

**Scope**
- Implement low-text-density heuristic.
- Trigger OCR fallback when threshold is met.
- Use PaddleOCR or approved OCR path.
- Persist OCR-used metadata.
- Keep page-aware or block-aware output when possible.

**Dependencies**
- US-014

**Acceptance criteria**
- Native-text PDFs do not unnecessarily OCR.
- Scanned PDFs and poor image extractions trigger OCR fallback.
- OCR status is visible in metadata and audit logs.

**Verification**
- Test with native PDF and scanned PDF fixtures.

**Tests**
- Unit tests for text density heuristic.
- Integration test for OCR fallback path.

---

### US-016 - Implement structured spreadsheet and CSV extraction enhancements

**User story**  
As a user, I want spreadsheet-aware extraction so sheet names, table ranges, and rows remain traceable in answers.

**Scope**
- Add `openpyxl` fallback or supplement for XLSX.
- Add `pandas` CSV normalization.
- Treat each worksheet as sub-document.
- Preserve metadata:
  - sheet name
  - range when possible
  - row numbers
  - headers
- Generate narrative text representation plus structured JSON snapshot.

**Dependencies**
- US-014

**Acceptance criteria**
- XLSX ingestion includes sheet-aware metadata.
- CSV ingestion retains header-aware row-group chunk source traceability.

**Verification**
- Index multi-sheet workbook and inspect chunk metadata.

**Tests**
- Fixture-based tests for spreadsheets and CSV.

---

### US-017 - Persist document, chunk, and ingestion metadata to PostgreSQL

**User story**  
As a system, I want normalized metadata persisted so downstream retrieval and UI features have a reliable source of truth.

**Scope**
- Implement SQLAlchemy models and migrations for PRD tables:
  - users
  - workspaces
  - workspace_members
  - files
  - ingestion_jobs
  - documents
  - chunks
  - chat_sessions
  - chat_messages
  - pending_chat_requests
  - citations
  - message_scopes
  - audit_events
- Persist ingestion outputs.

**Dependencies**
- US-003, US-013

**Acceptance criteria**
- Database schema is migrated successfully.
- File/document/chunk/job records are persisted correctly.

**Verification**
- Run migrations and inspect rows after ingestion.

**Tests**
- Migration tests if available.
- Repository or ORM model tests.

---

## Epic 6 - Chunking, Embeddings, and Vector Indexing

### US-018 - Implement hierarchical chunking service

**User story**  
As a system, I want documents chunked by structure before token size so retrieval stays meaningful and traceable.

**Scope**
- Split by file structure first.
- Split by page, sheet, or heading boundaries second.
- Split by token budget last.
- Respect configurable target chunk size and overlap.
- Prevent cross-page or cross-sheet merges unless explicitly allowed.

**Dependencies**
- US-014, US-016, US-017

**Acceptance criteria**
- Chunking preserves logical structure.
- Each chunk has required metadata.
- Token count and overlap are applied consistently.

**Verification**
- Inspect chunk outputs for PDF, DOCX, XLSX, and CSV fixtures.

**Tests**
- Unit tests for chunk boundaries.
- Golden tests for chunk metadata.

---

### US-019 - Implement embedding generation service

**User story**  
As a system, I want local embedding generation so I can search private content without external SaaS dependence.

**Scope**
- Load embedding model from config.
- Generate embeddings for chunks.
- Add retry logic around model calls.
- Record timing and model metadata.

**Dependencies**
- US-018

**Acceptance criteria**
- Embeddings are generated for chunk sets.
- Failures are captured cleanly and retried when appropriate.

**Verification**
- Embed test chunks and confirm vector dimensions match expected model output.

**Tests**
- Unit tests with mocked model.
- Integration test with configured model.

---

### US-020 - Implement Qdrant vector indexing and payload filtering

**User story**  
As a system, I want indexed vectors with payload metadata so retrieval can enforce workspace scoping and citation traceability.

**Scope**
- Create Qdrant collection.
- Upsert vectors with required payload:
  - chunk_id
  - file_id
  - workspace_id
  - source_type
  - page_number
  - sheet_name
  - section_heading
  - uploaded_by
  - parser_used
  - ocr_used
  - content_hash
- Add delete-by-file capability.

**Dependencies**
- US-019

**Acceptance criteria**
- Vectors are searchable by semantic similarity.
- Workspace and file filters are supported.
- Delete-by-file removes stale vectors.

**Verification**
- Index sample vectors and query by workspace/file filter.

**Tests**
- Integration tests for upsert, search, and delete.

---

## Epic 7 - Grounded Query and Citation Generation

### US-021 - Implement chat session and message persistence APIs

**User story**  
As a user, I want chat sessions saved so I can continue document conversations over time.

**Scope**
- Implement:
  - `POST /api/chat/sessions`
  - `GET /api/chat/sessions`
  - `GET /api/chat/sessions/{sessionId}`
- Persist chat messages for user and assistant roles.
- Enforce workspace/session ownership.

**Dependencies**
- US-017, US-005

**Acceptance criteria**
- Users can create and load sessions in their workspace.
- Messages persist across refresh.

**Verification**
- Create session, save messages, reload.

**Tests**
- Integration tests for session lifecycle.

---

### US-022 - Implement retrieval service with workspace and optional file scoping

**User story**  
As a system, I want scoped retrieval so grounded answers only use authorized chunks.

**Scope**
- Embed user question.
- Retrieve top-k from Qdrant.
- Enforce workspace filter always.
- Enforce file filter when `fileIds` are provided.
- Support optional rerank interface even if initial implementation is pass-through.
- Return ranked chunks and metadata.

**Dependencies**
- US-020, US-005

**Acceptance criteria**
- Retrieval never crosses workspace boundary.
- Retrieval can be restricted to explicit file selection.

**Verification**
- Query with and without `fileIds` and confirm scoping.

**Tests**
- Integration tests for filtered retrieval.

---

### US-023 - Implement grounded prompt builder and answer policy

**User story**  
As a platform owner, I want prompt construction rules that force grounded behavior so the assistant does not invent unsupported answers.

**Scope**
- Build prompt builder that formats retrieved chunks into context blocks.
- Add system prompt rules:
  - answer only from context
  - cite claims
  - say when evidence is insufficient
  - do not invent page numbers or facts
- Keep upload-and-ask prompt path identical to normal grounded path after indexing.

**Dependencies**
- US-022

**Acceptance criteria**
- Prompt format includes source labels with page/sheet metadata when available.
- No alternate raw-file prompt path exists for grounded mode.

**Verification**
- Inspect generated prompt for sample query.

**Tests**
- Unit tests for prompt builder formatting.

---

### US-024 - Implement private LLM service adapter

**User story**  
As an engineer, I want an internal LLM adapter so the chat system can swap inference backends without changing retrieval logic.

**Scope**
- Add service abstraction for LLM calls.
- Support configured base URL and model name.
- Support standard completion call and streaming response mode.
- Add retry and error handling.

**Dependencies**
- US-023

**Acceptance criteria**
- Query pipeline can invoke LLM via one internal adapter.
- Streaming mode works for supported backend.

**Verification**
- Run a mocked completion call and a live local call if model is available.

**Tests**
- Unit tests with mock transport.

---

### US-025 - Implement `POST /api/chat/query` grounded query endpoint

**User story**  
As a knowledge user, I want to ask questions over my documents so I receive grounded answers with citations.

**Scope**
- Validate request body:
  - `workspaceId`
  - `sessionId`
  - `question`
  - optional `fileIds`
  - `mode`
- Validate workspace and session authorization.
- Retrieve chunks.
- Build prompt.
- Generate answer.
- Persist assistant message and citations.
- Return answer plus citations.

**Dependencies**
- US-021, US-022, US-023, US-024

**Acceptance criteria**
- Valid grounded query returns answer and citations.
- Weak retrieval returns a grounded insufficiency answer, not hallucination.
- Unauthorized query is rejected.

**Verification**
- Ask a question tied to a known source and inspect citations.
- Ask unsupported question and inspect safe fallback answer.

**Tests**
- End-to-end integration tests for query flow.

---

### US-026 - Implement citation formatting and supporting chunk persistence

**User story**  
As a user, I want citations and supporting chunk previews so I can verify where an answer came from.

**Scope**
- Persist citations linked to assistant message.
- Persist message scope if needed.
- Generate display label data from source metadata.
- Return preview snippet for each citation.

**Dependencies**
- US-025

**Acceptance criteria**
- Every grounded answer includes citations when evidence exists.
- Citations reference correct file/page/sheet/section details.

**Verification**
- Compare retrieved chunk metadata to citation payload.

**Tests**
- Unit tests for citation formatter.

---

## Epic 8 - Upload-and-Ask Orchestration

### US-027 - Implement pending chat request persistence model and lifecycle

**User story**  
As a system, I want pending upload-and-ask requests stored durably so the first answer can execute after indexing completes.

**Scope**
- Implement pending request repository and schema.
- Store:
  - workspace ID
  - session ID
  - created by
  - question
  - mode
  - scope
  - file selection
  - status
  - timestamps
  - error message
- Support state transitions.

**Dependencies**
- US-017

**Acceptance criteria**
- Pending request can be created, updated, and queried independently of immediate answer generation.

**Verification**
- Insert and transition sample pending request.

**Tests**
- Repository tests for pending request states.

---

### US-028 - Implement `POST /api/chat/upload-and-ask`

**User story**  
As a knowledge user, I want to upload file(s) and ask the first question in one action so I do not need to wait for indexing manually.

**Scope**
- Accept file upload plus question in one request.
- Store raw files.
- Create file records, job records, and pending chat request.
- Default scope to `uploaded_files_only`.
- Return request ID and waiting state quickly.

**Dependencies**
- US-007, US-027

**Acceptance criteria**
- Endpoint returns before indexing completes.
- Pending request is persisted with correct file association.

**Verification**
- Call endpoint with one or more files and confirm `waiting_for_index` response.

**Tests**
- Integration test for upload-and-ask request creation.

---

### US-029 - Implement worker trigger for executing pending request after indexing completes

**User story**  
As a system, I want indexed files to automatically trigger blocked upload-and-ask requests so the first answer is generated without manual user retry.

**Scope**
- After file indexing completes, check for pending requests dependent on that file set.
- Trigger `execute_pending_chat_request` only when all required files are indexed.
- Do not execute if any required file failed or was deleted.

**Dependencies**
- US-028, US-020, US-025

**Acceptance criteria**
- Pending request auto-executes when blocking files are ready.
- Request does not execute prematurely.

**Verification**
- Upload two files in one request and ensure execution waits for both to index.

**Tests**
- Integration test for multi-file pending execution behavior.

---

### US-030 - Implement `GET /api/chat/upload-and-ask/{requestId}` status API

**User story**  
As a frontend client, I want to poll pending request state so I can show upload-and-ask progress even without websockets.

**Scope**
- Return request status.
- Return per-file statuses.
- Return answer-ready state.
- Return answer or message reference when completed.

**Dependencies**
- US-027, US-029

**Acceptance criteria**
- UI can poll and render status transitions accurately.

**Verification**
- Poll across full lifecycle from waiting to completed.

**Tests**
- Integration test for request state endpoint.

---

### US-031 - Enforce upload-and-ask grounding and scope guarantees

**User story**  
As a platform owner, I want the first upload-and-ask answer to obey the same grounding path and file scope rules as normal chat so privacy controls are preserved.

**Scope**
- Ensure first answer uses indexed chunk retrieval only.
- Ensure default scope is uploaded files only.
- Ensure no raw uploaded file body is sent directly to LLM.
- Allow workspace-scope expansion only through explicit future action.

**Dependencies**
- US-029

**Acceptance criteria**
- No code path bypasses retrieval for first answer.
- Retrieval scope is limited to uploaded file set by default.

**Verification**
- Inspect request execution path and test with workspace files outside upload set.

**Tests**
- Integration test proving retrieved chunks come only from uploaded file IDs.

---

## Epic 9 - Frontend Workspace and Document Library UX

### US-032 - Implement login page and protected app shell

**User story**  
As a user, I want a login page and protected shell so I can securely enter the application.

**Scope**
- Build login page.
- Implement route protection.
- Add session-aware app shell.

**Dependencies**
- US-004

**Acceptance criteria**
- Protected pages redirect unauthenticated users.
- Signed-in users reach workspace shell.

**Verification**
- Manual auth flow test.

**Tests**
- Frontend route protection tests if available.

---

### US-033 - Implement workspace dashboard page

**User story**  
As a user, I want a workspace dashboard so I can quickly see recent files, statuses, and chats.

**Scope**
- Build dashboard page.
- Show workspace selector.
- Show recent files and recent chats.
- Show ingestion status summary.

**Dependencies**
- US-010, US-021, US-032

**Acceptance criteria**
- Dashboard loads current workspace data.

**Verification**
- Seed data and inspect dashboard render.

**Tests**
- Component tests for loading and error states.

---

### US-034 - Implement document library page and filters

**User story**  
As a user, I want a document library so I can upload, inspect, filter, reprocess, and delete files.

**Scope**
- Build document table.
- Add filter controls for status, type, owner, upload date.
- Add file detail drawer.
- Wire reprocess and delete actions.

**Dependencies**
- US-010, US-011, US-012

**Acceptance criteria**
- Users can browse and manage files entirely from the library page.

**Verification**
- Manual test of filter, detail, reprocess, and delete flows.

**Tests**
- Component/integration tests for filter behavior and actions.

---

### US-035 - Implement drag-and-drop multi-file upload UX with progress and status badges

**User story**  
As a user, I want drag-and-drop uploads and visible progress so I know my files were accepted and are processing.

**Scope**
- Use drag-and-drop component.
- Support multi-file upload.
- Show per-file progress.
- Show backend status badges.
- Show failure reasons.

**Dependencies**
- US-007, US-009, US-034

**Acceptance criteria**
- Users can upload multiple files in one action.
- Status changes appear without full page refresh.

**Verification**
- Upload multiple supported and unsupported files.

**Tests**
- Frontend integration tests with mocked API.

---

## Epic 10 - Frontend Chat and Citation UX

### US-036 - Implement chat page with session list and message thread

**User story**  
As a user, I want a chat page so I can ask questions and revisit earlier answers.

**Scope**
- Build chat page.
- Show session list.
- Show active thread.
- Add input box and send action.

**Dependencies**
- US-021, US-025, US-032

**Acceptance criteria**
- User can create/select sessions and send questions.

**Verification**
- Manual test of session switch and question submit.

**Tests**
- Component tests for session/thread state.

---

### US-037 - Implement streaming answer UX and grounded error states

**User story**  
As a user, I want streaming responses and clear error handling so the system feels responsive and trustworthy.

**Scope**
- Add streaming support for query answers.
- Show generating/loading state.
- Show grounded insufficiency message distinctly from system errors.

**Dependencies**
- US-024, US-025, US-036

**Acceptance criteria**
- Query response starts rendering before full completion when streaming is enabled.
- System errors and no-evidence answers are distinguishable.

**Verification**
- Ask supported and unsupported questions.

**Tests**
- Frontend integration tests with mocked streaming.

---

### US-038 - Implement citation sidebar and chunk preview drawer

**User story**  
As a user, I want a citation panel and chunk previews so I can inspect the evidence behind an answer.

**Scope**
- Render citation list.
- Show file name, page/sheet, section, snippet.
- Show supporting chunk preview drawer.

**Dependencies**
- US-026, US-036

**Acceptance criteria**
- Every citation is clickable and reveals supporting context.

**Verification**
- Ask a question with multiple citations and inspect drawer content.

**Tests**
- UI component tests for citations.

---

### US-039 - Implement upload-and-ask UI flow on chat page

**User story**  
As a user, I want to upload file(s) and ask my first question in one chat action so the workflow feels like modern document chat.

**Scope**
- Add upload-and-ask control to chat page.
- Let user attach one or more files plus question.
- Show lifecycle states:
  - uploading
  - indexing
  - retrieving
  - generating
  - completed
  - failed
- Poll request status endpoint if needed.

**Dependencies**
- US-028, US-030, US-036

**Acceptance criteria**
- User sees clear progress from upload through first answer.
- First answer appears in same session thread.

**Verification**
- Manual end-to-end upload-and-ask test.

**Tests**
- Frontend integration tests for lifecycle state rendering.

---

## Epic 11 - Admin, Observability, and Reliability

### US-040 - Implement admin settings API and page

**User story**  
As an admin, I want to configure parser, chunking, embedding, and LLM settings so I can manage the system without code edits.

**Scope**
- Implement:
  - `GET /api/admin/settings`
  - `PUT /api/admin/settings`
- Build admin settings page.
- Manage at minimum:
  - parser settings
  - chunk size and overlap
  - embedding model name
  - LLM endpoint and model
  - vector store connection

**Dependencies**
- US-002, US-032

**Acceptance criteria**
- Admin can view and update settings.
- Invalid settings are rejected.

**Verification**
- Update a setting and confirm it is persisted and loaded.

**Tests**
- API tests for settings validation.

---

### US-041 - Implement job visibility, ingestion logs, and stage timing metrics

**User story**  
As an operator, I want job visibility and timing data so I can diagnose ingestion problems.

**Scope**
- Add structured logs containing:
  - request ID
  - workspace ID
  - file ID
  - job ID
  - parser used
  - stage name
  - duration ms
- Add API or admin page visibility into recent jobs.
- Capture metrics from PRD where practical.

**Dependencies**
- US-013, US-017

**Acceptance criteria**
- Operator can inspect failed jobs and per-stage timing.

**Verification**
- Trigger successful and failed jobs and inspect logs/visibility screen.

**Tests**
- Unit tests for logging helpers where feasible.

---

### US-042 - Implement retryable failure handling and idempotent worker safeguards

**User story**  
As a platform owner, I want reliable retries and idempotent job behavior so transient failures do not corrupt indexing state.

**Scope**
- Retry transient worker failures.
- Mark permanent failures cleanly.
- Prevent duplicate chunk/vector insertion on retry.
- Save debug artifact locations and error messages.

**Dependencies**
- US-013 through US-020

**Acceptance criteria**
- Retried jobs do not duplicate vectors or chunks.
- Permanent failures surface meaningful messages.

**Verification**
- Force transient failure and retry.
- Confirm single final indexed state.

**Tests**
- Integration tests for retry/idempotency.

---

## Epic 12 - End-to-End Integration and Golden Corpus Testing

### US-043 - Build golden test corpus and fixture loader

**User story**  
As an engineer, I want a standard fixture corpus so I can verify parsing, OCR, chunking, and citation behavior consistently.

**Scope**
- Add fixtures for:
  - native text PDF
  - scanned PDF
  - DOCX with headings and table
  - XLSX with multiple sheets
  - CSV large sample subset
  - PNG screenshot with text
  - JPEG invoice or form
- Add fixture loader utilities.

**Dependencies**
- US-014, US-015, US-016, US-018

**Acceptance criteria**
- Fixtures are reusable across parser, chunking, and e2e tests.

**Verification**
- Run fixture loader and confirm accessibility.

**Tests**
- Fixture smoke tests.

---

### US-044 - Create end-to-end ingestion test suite

**User story**  
As an engineer, I want end-to-end ingestion tests so I can verify upload through index behavior across supported file types.

**Scope**
- Test flow:
  - upload
  - parse
  - optional OCR
  - normalize
  - chunk
  - embed
  - index
- Validate metadata and final statuses.

**Dependencies**
- US-043, US-007 through US-020

**Acceptance criteria**
- Supported fixture types ingest successfully.
- Expected parser/OCR path is validated.

**Verification**
- Run full test suite locally.

**Tests**
- Full e2e ingestion tests.

---

### US-045 - Create end-to-end grounded query and upload-and-ask test suite

**User story**  
As an engineer, I want end-to-end query tests so I can prove grounded retrieval, citation accuracy, and upload-and-ask orchestration work correctly.

**Scope**
- Test standard grounded query.
- Test weak-evidence response path.
- Test file-scoped retrieval.
- Test upload-and-ask lifecycle.
- Test delete and reprocess effects on retrieval.

**Dependencies**
- US-025 through US-031, US-043

**Acceptance criteria**
- Query tests prove grounding guarantees and citation correctness.
- Upload-and-ask does not bypass indexing.

**Verification**
- Run complete e2e suite and inspect pass results.

**Tests**
- Full e2e query and orchestration tests.

---

# 7. Recommended Codex Session Assignment Packs

These packs are the safest way to split work across parallel sessions.

## Pack A - Platform Foundation
Assign:
- US-001
- US-002
- US-003
- US-017

Deliverables:
- repository structure
- Docker Compose
- shared config
- database models and migrations
- shared API schemas

Integration contract:
- Must publish all enums, schema types, and migration instructions first.

---

## Pack B - Auth and Authorization
Assign:
- US-004
- US-005
- US-006

Deliverables:
- auth flow
- workspace authorization helpers
- audit event service

Integration contract:
- Must expose middleware/dependency hooks used by all APIs.

---

## Pack C - Upload and Library Backend
Assign:
- US-007
- US-008
- US-009
- US-010

Deliverables:
- file upload API
- validation service
- file list/detail APIs
- job state handling

Integration contract:
- Must use shared file status enums from Pack A.

---

## Pack D - Worker and Parsing Pipeline
Assign:
- US-013
- US-014
- US-015
- US-016

Deliverables:
- Celery worker framework
- parser service
- OCR fallback
- spreadsheet-aware extraction

Integration contract:
- Must persist normalized artifacts and call Pack A database layer.

---

## Pack E - Chunking and Vector Indexing
Assign:
- US-018
- US-019
- US-020

Deliverables:
- chunking service
- embedding service
- Qdrant integration

Integration contract:
- Must accept normalized document inputs from Pack D and expose retrieval-ready indexing outputs.

---

## Pack F - Grounded Chat Backend
Assign:
- US-021
- US-022
- US-023
- US-024
- US-025
- US-026

Deliverables:
- chat sessions
- retrieval service
- prompt builder
- LLM adapter
- grounded query endpoint
- citation persistence

Integration contract:
- Must consume indexed vectors from Pack E and auth hooks from Pack B.

---

## Pack G - Upload-and-Ask Backend
Assign:
- US-027
- US-028
- US-029
- US-030
- US-031

Deliverables:
- pending request model
- upload-and-ask endpoint
- execution orchestration
- polling endpoint
- scope and grounding enforcement

Integration contract:
- Must call the same grounded query path from Pack F after indexing completes.

---

## Pack H - Frontend Shell and Document Library
Assign:
- US-032
- US-033
- US-034
- US-035

Deliverables:
- login shell
- dashboard
- document library
- upload UX

Integration contract:
- Can mock backend early but must adopt final schemas from Packs A, B, and C.

---

## Pack I - Frontend Chat Experience
Assign:
- US-036
- US-037
- US-038
- US-039

Deliverables:
- chat page
- streaming UX
- citation panel
- upload-and-ask UX

Integration contract:
- Must align to Pack F and Pack G payloads exactly.

---

## Pack J - Admin, Reliability, and Test Hardening
Assign:
- US-040
- US-041
- US-042
- US-043
- US-044
- US-045

Deliverables:
- admin page and settings APIs
- logs/metrics visibility
- retry/idempotency hardening
- fixture corpus
- e2e tests

Integration contract:
- Should start once core APIs stabilize, but can scaffold fixtures and test harness early.

---

# 8. Minimum Definition of Done for Every Story

A story is not done until all of the following are true:

1. Code is committed in the proper service or app.
2. Types/schemas align with shared contracts.
3. Automated tests exist and pass.
4. Error cases are handled explicitly.
5. Logging is present for important operations.
6. Local verification steps are documented.
7. No hardcoded secrets or environment-specific assumptions are introduced.
8. The story can be demonstrated independently.

---

# 9. Tech Lead Checklist Before Launching Parallel Codex Sessions

1. Lock enum names and payload contracts.
2. Decide auth approach for MVP.
3. Decide OCR policy for MVP.
4. Decide vector store implementation for MVP.
5. Confirm whether shared types are generated or manually mirrored.
6. Confirm whether streaming is SSE, fetch-streaming, or websocket-based.
7. Confirm whether admin settings are persisted in DB or env-backed for MVP.
8. Make one session responsible for integration conflict resolution.

---

# 10. Suggested Prompt Template for Each Codex Session

Use this when launching a parallel implementation session:

```text
You are implementing the Private LLM Workspace backlog.
Work only on the following user stories:
- [insert user story IDs]

Constraints:
- Honor the shared contracts in the backlog markdown.
- Do not rename enums or response shapes unless absolutely necessary.
- Keep changes scoped to your assigned stories.
- Add automated tests.
- Add brief implementation notes and verification steps.
- If a dependency is missing, stub behind an interface rather than blocking.

Your goal is to produce production-leaning MVP code that a competent engineer can run locally.
```

---

# 11. Final Delivery Standard

When all user stories are complete, the integrated system should satisfy the PRD acceptance criteria:
- async upload works
- supported files ingest successfully
- parsing and OCR fallback work
- chunks are embedded and indexed
- grounded chat returns cited answers
- workspace isolation holds
- reprocess and delete work cleanly
- upload-and-ask waits for indexing and uses the same grounded retrieval path

