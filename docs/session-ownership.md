# Session Ownership Boundaries

## Session A
- Owned directories:
  - `apps/web` (startup scaffold only)
  - `services/api` (startup scaffold only)
  - `services/workers` (startup scaffold only)
  - `services/shared`
  - `infra/docker`
  - `packages/shared-types`
  - `docs/contracts.md`
  - `docs/session-ownership.md`
  - `docs/integration-checklist.md`
- Forbidden scope:
  - upload, parser, retrieval, or UI business logic

## Session B
- Owned directories:
  - `services/api` auth, identity, workspace authorization middleware
- Must not modify without coordination:
  - frozen enums or shared contract field names

## Session C
- Owned directories:
  - `services/api` upload and file library endpoints/services
- Must not modify without coordination:
  - parser internals, embeddings, retrieval contracts

## Session D
- Owned directories:
  - `services/workers` ingestion orchestration and parser routing
- Must not modify without coordination:
  - vector indexing payload contracts owned by Session E

## Session E
- Owned directories:
  - `services/workers` chunking, embeddings, Qdrant indexing
- Must not modify without coordination:
  - upload API semantics, chat prompt logic

## Session F
- Owned directories:
  - `services/api` chat query, retrieval service contract, citation assembly
- Must not modify without coordination:
  - upload-and-ask lifecycle persistence owned by Session G

## Session G
- Owned directories:
  - `services/api` upload-and-ask orchestration and pending state APIs
  - `services/workers` triggers for post-index execution
- Must not modify without coordination:
  - auth core owned by Session B

## Session H
- Owned directories:
  - `apps/web` app shell and document library UX
- Must not modify without coordination:
  - chat interaction UX owned by Session I

## Session I
- Owned directories:
  - `apps/web` chat and citations UX
- Must not modify without coordination:
  - admin UX owned by Session J

## Session J
- Owned directories:
  - admin, observability, resilience, e2e test assets
- Must not modify without coordination:
  - frozen contract names unless critical integration blocker

## Shared merge rule
- Any change to frozen contracts (`packages/shared-types`, `services/shared/enums.py`, `services/shared/contracts.py`, `docs/contracts.md`) requires explicit integration acknowledgement from all active sessions.
