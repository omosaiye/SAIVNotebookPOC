# Integration Checklist

## 1. Startup sequence

1. Copy env templates:
   - `cp infra/docker/.env.example infra/docker/.env`
   - `cp .env.example .env`
   - `cp apps/web/.env.example apps/web/.env.local`
   - `cp services/api/.env.example services/api/.env`
   - `cp services/workers/.env.example services/workers/.env`
2. Install dependencies:
   - `npm install`
   - `python3 -m venv .venv && source .venv/bin/activate`
   - `pip install -r requirements.txt`
3. Start infrastructure:
   - `docker compose --env-file infra/docker/.env -f infra/docker/docker-compose.yml up -d`
4. Start API:
   - `set -a; source .env; set +a`
   - `uvicorn services.api.app.main:app --host 0.0.0.0 --port 8000 --reload`
5. Start workers:
   - `set -a; source .env; set +a`
   - `celery -A services.workers.app.celery_app:celery_app worker --loglevel=info`
6. Start web:
   - `npm run web:dev`

## 2. Smoke path

1. Run `./scripts/smoke/startup-smoke.sh`.
2. Confirm infra is healthy with `docker compose -f infra/docker/docker-compose.yml ps`.
3. Hit API health endpoint: `curl http://localhost:8000/health`.

## 3. Seed data steps

Not implemented in Session A. Downstream sessions should provide:
- workspace/user seed utilities
- sample file upload fixtures
- ingestion and retrieval fixtures

## 4. Known stubs and planned replacement

- Web app home page is scaffold-only. Session H/I will replace with product UX.
- API now exposes file library routes under `/api/v1/files` (upload, list, detail, status, reprocess, delete).
- Worker contains only `health.ping` Celery task. Sessions D/E/G will add ingestion/indexing jobs.
- No database migrations are included yet. Session B/C should add schema migrations.
