# Grounded Chat API Notes (Session F)

This document describes the backend behavior for chat persistence and grounded query execution.

## Implemented endpoints

- `POST /api/chat/sessions`
  - Creates a chat session for a workspace.
- `GET /api/chat/sessions?workspaceId={workspaceId}`
  - Lists sessions in a workspace, newest first.
- `GET /api/chat/sessions/{sessionId}?workspaceId={workspaceId}`
  - Loads a session and all persisted messages (with assistant citations).
- `POST /api/chat/query`
  - Executes grounded retrieval + prompt build + LLM generation.

## Grounded mode guarantees

- `mode` is enforced to `grounded` only.
- Workspace boundary is always applied in retrieval.
- Optional `fileIds` filter is applied when provided.
- If no evidence is found, API returns a grounded insufficiency answer.
- Raw file body pass-through is not used.

## Frontend-facing error states

`POST /api/chat/query` may return the following error codes:

- `SESSION_NOT_FOUND` (HTTP 404)
  - `chatSessionId` does not exist in the requested workspace.
- `MODE_NOT_SUPPORTED` (HTTP 422)
  - Request mode is not `grounded`.
- `LLM_BACKEND_ERROR` (HTTP 502)
  - Internal LLM endpoint call failed after retries.

The API can also return a successful response (`200`) with:

- `errorCode: "RETRIEVAL_EMPTY"`
- grounded insufficiency `answer`
- empty `citations`

This indicates a valid request with insufficient evidence, not a transport/system failure.

## Citation payload

Citations returned for assistant messages follow canonical contract fields:

- `fileId`
- `fileName`
- `page`
- `sheetName`
- `sectionHeading`
- `snippet`
- `chunkId`
- `score`

Supporting chunk metadata is persisted in the retrieval store and transformed to citation response objects during answer persistence.
