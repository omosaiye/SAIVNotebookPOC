# Codex Operator Sheet - Private LLM Workspace

## The one rule
Do not start implementation in Sessions B, C, D, or F until Session A has finished and the shared contracts are frozen.

You may prepare those sessions early (create branches, paste prompts, stage context), but do not let them invent schemas, enums, payloads, or status transitions before Session A lands.

## Launch order
1. Session A only
2. Review and merge Session A
3. Freeze contracts
4. Launch Sessions B, C, D, and F in parallel
5. Review and merge B, C, D, F
6. Launch Sessions E and G
7. Review and merge E and G
8. Launch Sessions H and I
9. Review and merge H and I
10. Launch Session J
11. Run full end-to-end validation
12. Stabilize and cut release candidate

## Hard gate before B/C/D/F
Session A must deliver all of the following:
- monorepo scaffolding
- local Docker infrastructure
- `.env.example` files
- shared enums
- shared request and response contracts
- documented status transitions
- `CONTRACTS.md` or equivalent

## Session ownership
- A: foundation and contracts
- B: auth and authorization
- C: upload and document library backend
- D: ingestion and parser pipeline
- E: chunking, embeddings, vector indexing
- F: grounded chat backend and citations
- G: upload-and-ask orchestration
- H: web shell and document library UI
- I: chat UI and citation UX
- J: admin, observability, resilience, end-to-end tests

## Merge rule
Merge by wave, not by arrival time.
Do not merge a later-wave session ahead of an earlier-wave dependency unless it is explicitly stub-safe and reviewed.

## What to ask every session to return
- code changes only for its assigned stories
- automated tests
- run instructions
- assumptions made
- files created or changed
- handoff notes for dependent sessions
- known gaps or stubs

## Review checklist before each merge
- story scope respected
- no contract drift
- tests pass locally
- env vars documented
- logs/errors understandable
- no unrelated refactors
- handoff notes included

## If a session is blocked
- stub the dependency behind an interface
- leave a TODO with the dependent story ID
- do not redesign the frozen contract
- move forward on isolated logic and tests

## Definition of success
A user can log in, enter a workspace, upload files, watch ingestion complete, ask grounded questions, see citations, and use upload-and-ask end to end with observable job status and passing end-to-end tests.
