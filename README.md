# Private LLM Workspace Monorepo

Foundation scaffold for the private LLM workspace project.

Implemented in Session A:
- US-001: monorepo structure and local environment bootstrap
- US-002: shared typed configuration for API and workers
- US-003: frozen shared enums and contract models

Implemented in Session B:
- US-004: baseline auth login and bearer session validation
- US-005: workspace membership authorization dependency for protected endpoints
- US-006: audit event recording for auth and API mutating actions

Implemented in Session F:
- US-021: chat session and message persistence APIs (in-memory)
- US-022, US-023, US-024: retrieval, prompting, and LLM adapter interfaces with local stub implementations
- US-025: grounded query endpoint at `POST /api/v1/chat/query`
- US-026: citation assembly from retrieved chunks

## Repository layout

- `apps/web` - Next.js startup scaffold
- `services/api` - FastAPI startup scaffold
- `services/workers` - Celery startup scaffold
- `services/shared` - shared Python config, enums, and Pydantic contracts
- `packages/shared-types` - shared TypeScript enums and contract interfaces
- `infra/docker` - local infrastructure compose stack (Postgres, Redis, MinIO, Qdrant)
- `docs` - contracts, ownership, and integration checklists

## Prerequisites

- Node.js 23+
- npm 10+
- Python 3.13+
- Docker + Docker Compose

## 1. Local setup

1. Copy environment templates:

```bash
cp infra/docker/.env.example infra/docker/.env
cp .env.example .env
cp apps/web/.env.example apps/web/.env.local
cp services/api/.env.example services/api/.env
cp services/workers/.env.example services/workers/.env
```

2. Install dependencies:

```bash
npm install
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Start infrastructure

```bash
docker compose --env-file infra/docker/.env -f infra/docker/docker-compose.yml up -d
```

Services:
- Postgres: `localhost:5432`
- Redis: `localhost:6379`
- MinIO API: `localhost:9000`
- MinIO console: `localhost:9001`
- Qdrant: `localhost:6333`

## 3. Run API, worker, and web

Use a separate terminal for each command.

API:

```bash
set -a; source .env; set +a
uvicorn services.api.app.main:app --host 0.0.0.0 --port 8000 --reload
```

Worker:

```bash
set -a; source .env; set +a
celery -A services.workers.app.celery_app:celery_app worker --loglevel=info
```

Web:

```bash
npm run web:dev
```

## 4. Smoke checks

```bash
./scripts/smoke/startup-smoke.sh
```

What this validates:
- required foundation files exist
- canonical enum contracts are frozen and aligned
- Python service modules compile
- Docker Compose configuration resolves

## 5. Auth quickstart (development seed user)

1. Login:

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"owner@local.dev","password":"dev-password"}'
```

2. Use `accessToken` as:

```bash
Authorization: Bearer <accessToken>
```

3. Pass `X-Workspace-Id` for protected routes.

## 6. Baseline quality commands

TypeScript:

```bash
npm run typecheck
npm run lint
npm run format
```

Python:

```bash
python3 -m ruff check .
python3 -m ruff format --check .
python3 -m pytest
```

## 7. Contract references

- Frozen enums and payload contracts: `docs/contracts.md`
- Session boundaries: `docs/session-ownership.md`
- Integration runbook: `docs/integration-checklist.md`

## 8. Intentional stubs in this phase

- Retrieval and LLM execution currently use local stub implementations pending full production adapters
- Frontend product UX is still scaffold-level (Sessions H/I pending)
- No production deployment manifests
- No database migrations yet
