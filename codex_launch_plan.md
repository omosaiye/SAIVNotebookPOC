# Codex Launch Plan - Private LLM Workspace

## 1. Purpose

This document translates the execution backlog into an operator-ready launch plan for running multiple Codex sessions in parallel as independent collaborating agents.

Use this document to:
- decide which Codex sessions to start first
- give each session an exact user story bundle
- prevent sessions from colliding on contracts and shared files
- define merge order and integration checkpoints
- keep junior-engineer-level execution disciplined and testable

This launch plan assumes the source backlog is:

- `private_llm_user_stories.md`

and that the target system remains:

- **Frontend:** Next.js + TypeScript
- **Backend:** FastAPI + Pydantic + SQLAlchemy
- **Workers:** Celery + Redis
- **Persistence:** PostgreSQL + S3-compatible object storage + Qdrant
- **Parsing:** Docling-first with fallbacks
- **Embeddings:** sentence-transformers
- **Inference:** private LLM service via internal adapter

---

## 2. Core Operating Principle

Do **not** run Codex as a swarm of loosely directed coding chats.

Run Codex as a controlled multi-session build program where each session:
1. owns a bounded set of user stories
2. implements only within an agreed surface area
3. writes tests for its own slice
4. emits clear handoff notes for integration
5. does not refactor another session's work unless explicitly assigned

The fastest way to lose time is to let multiple sessions modify shared contracts at the same time.

---

## 3. Recommended Session Topology

### Recommended session count

Start with **7 active Codex sessions** in Wave 1 and Wave 2, then expand to **10 sessions** only after shared contracts are frozen.

This gives you enough parallelism without creating merge chaos.

### Session map

| Session | Focus | Primary Stories |
|---|---|---|
| A | Foundation and shared contracts | US-001, US-002, US-003 |
| B | Auth and authorization | US-004, US-005, US-006 |
| C | Upload and library backend | US-007, US-008, US-009, US-010, US-011, US-012 |
| D | Worker and ingestion pipeline | US-013, US-014, US-015, US-016, US-017 |
| E | Chunking and vector indexing | US-018, US-019, US-020 |
| F | Chat backend and grounding | US-021, US-022, US-023, US-024, US-025, US-026 |
| G | Upload-and-ask orchestration | US-027, US-028, US-029, US-030, US-031 |
| H | Web shell and library UX | US-032, US-033, US-034, US-035 |
| I | Chat UX and citations UX | US-036, US-037, US-038, US-039 |
| J | Admin, observability, resilience, end-to-end | US-040, US-041, US-042, US-043, US-044, US-045 |

---

## 4. Execution Waves

## Wave 0 - Contract Freeze

### Goal
Lock the repo structure, env model, shared enums, and canonical request/response shapes before parallel coding begins.

### Active session
- **Session A only**

### Stories
- US-001
- US-002
- US-003

### Exit criteria
Do not start the other sessions until Session A has produced all of the following:

1. monorepo scaffolding
2. Docker Compose with working local infrastructure
3. `.env.example` files
4. shared enums
5. shared Pydantic or TypeScript contracts for:
   - file statuses
   - pending request statuses
   - chat mode
   - upload-and-ask scope
   - citation payload
6. a short `CONTRACTS.md` or `shared-types/README.md` that documents:
   - canonical enum values
   - API payload shapes
   - status transitions
   - what is frozen vs extensible

### Why this matters
Without this step, every later session will invent its own shape for file status, citations, and chat request payloads.

---

## Wave 1 - Backend Spine

### Goal
Build the minimum backend spine in parallel.

### Sessions to start after Wave 0 exits
- Session B
- Session C
- Session D
- Session F

### Stories
- **Session B:** US-004, US-005, US-006
- **Session C:** US-007 to US-012
- **Session D:** US-013 to US-017
- **Session F:** US-021 to US-026

### Notes
- Session F may stub retrieval and LLM internals behind interfaces until Session E and Session D complete.
- Session C and Session D should agree early on the upload-to-job enqueue contract.
- Session B should provide a reusable authorization dependency or guard layer before Session C and Session F lock endpoints.

### Exit criteria
Wave 1 is complete when:
- auth works
- upload APIs work
- worker skeleton runs
- parser framework is wired
- chat persistence exists
- grounded query endpoint shape exists, even if retrieval is temporarily mocked

---

## Wave 2 - Retrieval and Orchestration

### Goal
Attach real retrieval and async upload-and-ask behavior.

### Sessions to start
- Session E
- Session G

### Stories
- **Session E:** US-018, US-019, US-020
- **Session G:** US-027, US-028, US-029, US-030, US-031

### Notes
- Session E depends on Session D's document and chunk persistence shape.
- Session G depends on Session C, D, and F, but can begin with interface stubs once endpoint contracts are frozen.

### Exit criteria
Wave 2 is complete when:
- indexed chunks can be retrieved from Qdrant with workspace and optional file filtering
- upload-and-ask requests persist and transition correctly
- pending requests can execute automatically after indexing completes
- scope guarantees are enforced

---

## Wave 3 - Frontend Parallelization

### Goal
Build the user-facing app shell and workflows once API contracts are stable.

### Sessions to start
- Session H
- Session I

### Stories
- **Session H:** US-032, US-033, US-034, US-035
- **Session I:** US-036, US-037, US-038, US-039

### Notes
- Session H should own shared layout, navigation, upload entry points, and document library views.
- Session I should own chat interactions, answer rendering, citation interactions, and upload-and-ask UX.
- Both sessions should consume a typed API client generated or maintained from the frozen backend contracts.

### Exit criteria
Wave 3 is complete when:
- a user can log in
- enter a workspace
- upload files
- see file status
- ask grounded questions
- view citations
- use upload-and-ask end to end from the UI

---

## Wave 4 - Reliability and System Tests

### Goal
Harden the system and prove it works end to end.

### Session to start
- Session J

### Stories
- US-040
- US-041
- US-042
- US-043
- US-044
- US-045

### Notes
- Session J should start lightly in parallel by preparing fixtures and test harnesses after Wave 1.
- But final stabilization should happen after Waves 2 and 3 have converged.

### Exit criteria
Wave 4 is complete when:
- admin page and settings work
- job visibility and timing metrics work
- retries and idempotency protections exist
- golden test corpus exists
- end-to-end ingestion and grounded query tests pass

---

## 5. Merge Strategy

## Branch model

Use one integration branch and one branch per session.

- `main` - protected
- `integration/private-llm` - rolling integration branch
- `codex/session-a-foundation`
- `codex/session-b-auth`
- `codex/session-c-upload`
- `codex/session-d-ingestion`
- `codex/session-e-indexing`
- `codex/session-f-chat`
- `codex/session-g-upload-and-ask`
- `codex/session-h-web-library`
- `codex/session-i-web-chat`
- `codex/session-j-admin-e2e`

### Rule
Every Codex session branches from the latest `integration/private-llm`, not from stale work.

## Merge order

Recommended order:

1. Session A
2. Session B
3. Session C
4. Session D
5. Session F
6. Session E
7. Session G
8. Session H
9. Session I
10. Session J

### Why this order
It follows the dependency chain while still allowing parallel work.

### Merge gate for each session
Do not merge a session until it provides:

- completed user story list
- changed files summary
- run instructions
- tests added
- tests passing locally
- open assumptions
- deferred issues
- API or schema changes, if any

---

## 6. Ownership Boundaries

These boundaries are important. They reduce collisions.

## Session A owns
- repo scaffolding
- Docker Compose
- shared config
- shared types
- frozen enums
- cross-service contract docs

### Session A should not own
- business logic for uploads, parsing, chat, or UI

## Session B owns
- auth middleware
- identity extraction
- workspace membership enforcement
- audit event logging

### Session B should not own
- upload or chat endpoint business logic beyond applying auth guards

## Session C owns
- upload endpoint
- file validation
- object storage write path
- file listing
- reprocess and delete APIs
- upload state changes

### Session C should not own
- parser internals
- embeddings
- retrieval logic

## Session D owns
- worker framework
- parser orchestration
- OCR fallback routing
- structured file extraction
- persistence of ingestion metadata

### Session D should not own
- vector indexing
- answer generation
- frontend

## Session E owns
- chunking
- embedding generation
- vector indexing in Qdrant
- payload filtering shape in vector store

### Session E should not own
- upload API
- worker queue framework
- chat prompt assembly

## Session F owns
- chat sessions and messages
- retrieval service contract
- prompt builder
- LLM adapter
- grounded query execution
- citation payloads

### Session F should not own
- upload-and-ask lifecycle management
- UI rendering

## Session G owns
- pending request persistence
- upload-and-ask endpoint
- indexing completion trigger
- status polling endpoint
- scope enforcement for upload-and-ask

### Session G should not own
- base upload API
- core chat prompt logic

## Session H owns
- login page
- app shell
- workspace dashboard
- document library
- upload UX
- library filters and status badges

### Session H should not own
- answer rendering logic
- citation drawer behavior

## Session I owns
- chat page
- streaming answer rendering
- citation sidebar and preview drawer
- upload-and-ask interaction flow

### Session I should not own
- document library page structure
- backend contracts

## Session J owns
- admin settings page
- observability surfaces
- retry safeguards
- fixtures
- e2e tests
- reliability pass

### Session J should not own
- contract redesign unless critical for integration

---

## 7. Required Shared Artifacts

Before or during execution, create these shared artifacts in the repo.

### 7.1 `docs/contracts.md`
Must include:
- enum values
- API route list
- request and response payload examples
- file lifecycle transitions
- upload-and-ask lifecycle transitions

### 7.2 `docs/session-ownership.md`
Must include:
- each session
- owned directories
- forbidden directories except for small glue changes
- merge approver rules if you are using PR review

### 7.3 `docs/integration-checklist.md`
Must include:
- service startup sequence
- seed data steps
- smoke test path
- known stubs and what replaces them

### 7.4 `docs/test-matrix.md`
Must include:
- which stories have unit tests
- which stories have integration tests
- which stories are verified only through e2e
- who owns fixing a failing area

---

## 8. Definition of Done for Every Codex Session

A session is not done because code was generated.

A session is done only when all of the following are present:

1. **Story coverage**
   - every assigned user story is addressed
   - any skipped criteria are explicitly listed

2. **Code quality**
   - code compiles or runs
   - no placeholder TODOs in critical logic unless documented

3. **Tests**
   - unit or integration tests exist for core behavior
   - edge cases are covered where the story implies risk

4. **Run instructions**
   - exact commands for local execution are included

5. **Verification notes**
   - a junior engineer can manually verify the story from the instructions

6. **Handoff note**
   - assumptions
   - interfaces exposed
   - follow-up work for dependent sessions

---

## 9. Session Prompt Template

Use this template when launching each Codex session.

```text
You are working in a shared monorepo for a private LLM workspace product.

Your assignment is to implement only the user stories listed below from the execution backlog and launch plan.

Read these source documents first:
1. private_llm_user_stories.md
2. codex_launch_plan.md
3. docs/contracts.md if present
4. docs/session-ownership.md if present

Your assigned session:
[SESSION NAME]

Your assigned stories:
[STORY IDS AND TITLES]

Your goals:
- implement the assigned stories completely
- keep changes within your ownership boundary
- do not refactor unrelated code
- do not change canonical enums or payload shapes unless absolutely necessary
- write tests for your slice
- update docs only where your slice requires it
- leave clear handoff notes for integration

Mandatory output at the end:
1. summary of completed stories
2. files changed
3. tests added and how to run them
4. manual verification steps
5. assumptions and deferred issues

If a dependency is incomplete, stub it behind a clean interface and continue.
Prefer additive changes over refactors.
```

---

## 10. Ready-to-Paste Session Prompts

## Session A prompt

```text
You are Session A - Foundation and Shared Contracts.

Implement:
- US-001 - Initialize monorepo structure and local developer environment
- US-002 - Create shared configuration system
- US-003 - Define shared enums and schema contracts

Your ownership:
- apps/web scaffolding only as needed for startup
- services/api startup scaffolding
- services/workers startup scaffolding
- infra/docker
- packages/shared-types or equivalent
- docs/contracts.md
- docs/session-ownership.md
- docs/integration-checklist.md

Do not implement business logic for upload, parsing, retrieval, or UI features.

Your deliverables:
- working Docker Compose for Postgres, Redis, MinIO, Qdrant
- root README with local startup
- .env.example files
- canonical enums and status values
- shared request and response contract models
- contract documentation

Tests:
- smoke tests or health checks proving infra and app startup work

At the end, output:
- completed stories
- files changed
- startup commands
- tests run
- frozen contracts summary
- any areas still intentionally stubbed
```

## Session B prompt

```text
You are Session B - Authentication and Authorization.

Implement:
- US-004 - Implement baseline authentication flow
- US-005 - Implement workspace membership and authorization checks
- US-006 - Add audit event recording for security-relevant actions

Assume Session A has frozen shared contracts and config.

Your ownership:
- auth middleware
- identity extraction
- workspace authorization dependencies
- audit event persistence and logging
- any auth-related backend tests

Do not own upload, parser, retrieval, or UI feature logic except minimal glue.

Requirements:
- use the shared config and enums
- expose reusable authorization helpers for other endpoints
- make audit recording easy for other sessions to invoke

At the end, output:
- completed stories
- files changed
- auth flow summary
- how other sessions should apply authorization guards
- tests added and run commands
- manual verification steps
```

## Session C prompt

```text
You are Session C - Upload and Document Library Backend.

Implement:
- US-007 - Implement file upload API with async enqueue behavior
- US-008 - Implement file type validation and signature detection
- US-009 - Implement upload status tracking and ingestion job states
- US-010 - Implement file listing and filtering API
- US-011 - Implement file reprocess API and clean replacement behavior
- US-012 - Implement file delete API with tombstone/cleanup behavior

Assume Session A and Session B outputs exist.

Your ownership:
- upload endpoints
- object storage write path
- file metadata persistence
- status transitions at upload/API level
- list/filter/reprocess/delete APIs

Do not implement parser internals, chunking, embeddings, retrieval, or frontend screens.

Requirements:
- enqueue ingestion jobs through a clean interface
- use canonical file statuses
- document API payloads if your slice adds route examples
- honor workspace authorization

At the end, output:
- completed stories
- files changed
- API routes implemented
- status transition summary
- tests added and run commands
- manual verification steps
- integration notes for Session D and Session H
```

## Session D prompt

```text
You are Session D - Worker and Ingestion Pipeline.

Implement:
- US-013 - Implement worker framework and job orchestration skeleton
- US-014 - Implement Docling-first parser service
- US-015 - Implement OCR fallback trigger and execution path
- US-016 - Implement structured spreadsheet and CSV extraction enhancements
- US-017 - Persist document, chunk, and ingestion metadata to PostgreSQL

Assume Session A exists. Coordinate with Session C via frozen job enqueue contracts.

Your ownership:
- worker service
- Celery jobs
- parser orchestration
- OCR fallback path
- extraction pipeline
- ingestion persistence models and repositories

Do not implement vector indexing or answer generation.

Requirements:
- preserve parser metadata needed downstream
- persist the required chunk metadata fields from the backlog
- make failures retryable where appropriate
- expose a clean downstream handoff for chunking/indexing

At the end, output:
- completed stories
- files changed
- worker entrypoints
- parser pipeline summary
- supported file types and fallbacks
- tests added and run commands
- manual verification steps
- integration notes for Session E and Session G
```

## Session E prompt

```text
You are Session E - Chunking, Embeddings, and Vector Indexing.

Implement:
- US-018 - Implement hierarchical chunking service
- US-019 - Implement embedding generation service
- US-020 - Implement Qdrant vector indexing and payload filtering

Assume Session D provides parsed document content and metadata.

Your ownership:
- chunking logic
- embedding generation
- Qdrant write path
- vector payload schema and filters
- tests for retrieval-readiness of indexed chunks

Do not implement upload APIs, worker queue setup, or prompt assembly.

Requirements:
- preserve workspace and file scoping fields in vector payloads
- use deterministic chunk ordering where possible
- make indexing idempotent

At the end, output:
- completed stories
- files changed
- chunk schema summary
- Qdrant payload summary
- tests added and run commands
- manual verification steps
- integration notes for Session F and Session G
```

## Session F prompt

```text
You are Session F - Chat Backend and Grounding.

Implement:
- US-021 - Implement chat session and message persistence APIs
- US-022 - Implement retrieval service with workspace and optional file scoping
- US-023 - Implement grounded prompt builder and answer policy
- US-024 - Implement private LLM service adapter
- US-025 - Implement POST /api/chat/query grounded query endpoint
- US-026 - Implement citation formatting and supporting chunk persistence

Assume Session A exists. If Session E is incomplete, stub retrieval behind a clean interface and continue.

Your ownership:
- chat persistence
- retrieval service interface and implementation
- prompt building
- LLM adapter
- grounded answer execution
- citation assembly and persistence

Do not implement upload-and-ask lifecycle or frontend rendering.

Requirements:
- enforce grounded mode
- support optional fileIds scoping
- return the canonical citation payload
- document error states for frontend consumers

At the end, output:
- completed stories
- files changed
- endpoint summary
- retrieval and grounding flow summary
- tests added and run commands
- manual verification steps
- integration notes for Session G and Session I
```

## Session G prompt

```text
You are Session G - Upload-and-Ask Orchestration.

Implement:
- US-027 - Implement pending chat request persistence model and lifecycle
- US-028 - Implement POST /api/chat/upload-and-ask
- US-029 - Implement worker trigger for executing pending request after indexing completes
- US-030 - Implement GET /api/chat/upload-and-ask/{requestId} status API
- US-031 - Enforce upload-and-ask grounding and scope guarantees

Assume Session C, Session D, and Session F interfaces exist or can be stubbed.

Your ownership:
- pending request model
- upload-and-ask orchestration endpoint
- completion trigger wiring
- request status polling
- scope enforcement

Do not re-implement upload storage, parser internals, or base grounded query logic.

Requirements:
- use canonical pending request statuses
- preserve request-file linkage
- guarantee uploaded_files_only versus workspace scope behavior
- document exact lifecycle transitions

At the end, output:
- completed stories
- files changed
- lifecycle summary
- tests added and run commands
- manual verification steps
- integration notes for Session H and Session I
```

## Session H prompt

```text
You are Session H - Web Shell and Document Library UX.

Implement:
- US-032 - Implement login page and protected app shell
- US-033 - Implement workspace dashboard page
- US-034 - Implement document library page and filters
- US-035 - Implement drag-and-drop multi-file upload UX with progress and status badges

Assume backend contracts are frozen.

Your ownership:
- app shell
- navigation
- login page
- workspace dashboard
- document library page
- upload UX
- typed frontend API client usage for your pages

Do not own chat answer rendering or citation drawer behavior.

Requirements:
- reflect canonical file statuses in the UI
- surface upload failures clearly
- keep components modular so chat pages can reuse shell/layout

At the end, output:
- completed stories
- files changed
- routes/pages added
- tests added and run commands
- manual verification steps
- integration notes for Session I
```

## Session I prompt

```text
You are Session I - Chat UX and Citations UX.

Implement:
- US-036 - Implement chat page with session list and message thread
- US-037 - Implement streaming answer UX and grounded error states
- US-038 - Implement citation sidebar and chunk preview drawer
- US-039 - Implement upload-and-ask UI flow on chat page

Assume Session F and Session G contracts are stable. Reuse the shared app shell from Session H.

Your ownership:
- chat page
- session/message rendering
- streaming answer handling
- citation sidebar
- chunk preview drawer
- upload-and-ask interactions

Do not redesign the shared app shell or document library pages.

Requirements:
- handle grounded errors explicitly
- render citations using the canonical payload
- keep upload-and-ask interactions understandable for users
- use a typed API client and avoid hardcoded payload assumptions

At the end, output:
- completed stories
- files changed
- routes/pages/components added
- tests added and run commands
- manual verification steps
- integration notes and any UX assumptions
```

## Session J prompt

```text
You are Session J - Admin, Observability, Resilience, and End-to-End Validation.

Implement:
- US-040 - Implement admin settings API and page
- US-041 - Implement job visibility, ingestion logs, and stage timing metrics
- US-042 - Implement retryable failure handling and idempotent worker safeguards
- US-043 - Build golden test corpus and fixture loader
- US-044 - Create end-to-end ingestion test suite
- US-045 - Create end-to-end grounded query and upload-and-ask test suite

Assume most backend and frontend surfaces now exist.

Your ownership:
- admin settings features
- observability surfaces
- resilience safeguards
- golden fixtures
- integration and end-to-end tests

Do not do large refactors unless required to make the system testable and stable.

Requirements:
- produce a reliable golden corpus
- prove ingestion works end to end
- prove grounded query and upload-and-ask work end to end
- document what failures are retryable and how idempotency is enforced

At the end, output:
- completed stories
- files changed
- tests added and how to run them
- fixture/golden corpus summary
- manual verification steps
- residual risks before production hardening
```

---

## 11. Integration Checkpoints

Use these checkpoints to keep the parallel program under control.

## Checkpoint 1 - After Session A merge
Confirm:
- local repo boots
- contracts are frozen
- all later sessions can import shared config and enums

## Checkpoint 2 - After Sessions B, C, D, F merge
Confirm:
- authorized upload works
- files persist and enqueue jobs
- worker can process at least one file type
- chat persistence and grounded query route exist

## Checkpoint 3 - After Sessions E and G merge
Confirm:
- parsed content becomes indexed content
- grounded query can use real retrieval
- upload-and-ask can wait, complete, and return answer payloads

## Checkpoint 4 - After Sessions H and I merge
Confirm:
- user can complete primary UI workflows without raw API calls

## Checkpoint 5 - After Session J merge
Confirm:
- full system works under test harness
- logs and retry behavior are understandable
- there is a golden path demo scenario

---

## 12. Demo Script for Final Verification

This is the minimum demo sequence you should be able to run after full integration.

1. start local infrastructure
2. start web, api, and worker services
3. log in as a valid user
4. enter a workspace
5. upload one PDF and one spreadsheet
6. watch status progress from uploaded to indexed
7. open chat and ask a grounded question against workspace content
8. confirm answer returns citations
9. open citation preview and inspect chunk metadata
10. run upload-and-ask with a newly uploaded file
11. poll until request completes
12. confirm result is grounded and scope-correct
13. delete or reprocess a file
14. confirm status and cleanup behavior
15. run end-to-end tests

---

## 13. Risk Register for Parallel Codex Execution

## Risk 1 - Contract drift
**Cause:** multiple sessions invent different payloads  
**Mitigation:** Wave 0 freeze, docs/contracts.md, typed shared models

## Risk 2 - Merge collisions
**Cause:** overlapping ownership of shared files  
**Mitigation:** session ownership rules, additive changes, integration branch rebasing

## Risk 3 - Retrieval built before ingestion shape stabilizes
**Cause:** Session E and F race ahead of Session D  
**Mitigation:** interface stubs and delayed implementation of concrete adapters

## Risk 4 - Frontend hardcodes unstable backend payloads
**Cause:** UI sessions start before contracts stabilize  
**Mitigation:** start H and I only after Wave 2 contracts are reliable

## Risk 5 - Weak test coverage hides lifecycle bugs
**Cause:** sessions focus only on code generation  
**Mitigation:** enforce tests and manual verification notes for every session

---

## 14. Recommended Daily Operating Rhythm

If you are running this personally as engineering lead:

### Morning
- review previous session outputs
- merge only contract-safe work
- refresh `integration/private-llm`
- launch or relaunch the next Codex sessions with exact prompts

### Midday
- review handoff notes
- compare changed files against ownership boundaries
- reject scope creep quickly

### End of day
- run integration smoke tests
- update `docs/integration-checklist.md`
- decide which sessions can proceed versus need rerun

---

## 15. Fastest Practical Start Plan

If you want the shortest route to progress, do this:

### First launch
- Session A only

### Second launch, after A merges
- Session B
- Session C
- Session D
- Session F

### Third launch, after backend spine stabilizes
- Session E
- Session G

### Fourth launch, after retrieval and upload-and-ask contracts stabilize
- Session H
- Session I

### Final launch
- Session J

This is the safest path with strong parallelism and limited rework.

---

## 16. What You Should Tell Codex Every Time

Every session should be told the same hard rules:

1. implement only assigned stories
2. honor frozen contracts
3. prefer additive changes
4. write tests
5. leave handoff notes
6. do not refactor across session boundaries
7. if blocked, stub the dependency and continue
8. output exact verification steps for a junior engineer

That discipline matters more than the model.

---

## 17. Final Recommendation

Start with **Session A immediately** and do not launch the rest until:
- the repo boots
- contracts are written down
- canonical enums and payloads are frozen

Then run the rest in waves, not all at once.

That is the difference between parallel delivery and parallel confusion.
