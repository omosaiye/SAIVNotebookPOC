# POC Ready Runbook

This runbook captures the minimum repeatable flow to boot, verify, and demo the current POC.

## 1. Start local stack

```bash
make infra-up
```

In separate terminals:

```bash
set -a; source .env; set +a
make api
```

```bash
set -a; source .env; set +a
make worker
```

```bash
make web
```

Defaults:
- API: `http://localhost:8010`
- Web: `http://localhost:3000`

## 2. Load fixture corpus

```bash
./scripts/fixtures/load_golden_corpus.sh
```

## 3. Quick validation checks

```bash
curl http://localhost:8010/health
curl -X POST http://localhost:8010/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"owner@local.dev","password":"dev-password"}'
```

Then verify routes return `200`:
- `http://localhost:3000/workspace`
- `http://localhost:3000/chat`
- `http://localhost:3000/admin`

## 4. Manual product checks

1. `/workspace`
- uploaded golden files are listed
- statuses are visible
- upload/reprocess/delete controls are available

2. `/chat`
- grounded question returns an answer
- citations are shown
- upload-and-ask status transitions are visible

3. `/admin`
- runtime settings can be read/updated
- ingestion jobs and logs are populated
- metrics (queue depth/status counts/citation %) are visible

## 5. Known caveats

- `localhost:8000` may be occupied by Docker Desktop on some machines; this repo defaults API to `8010`.
- Qdrant may show `unhealthy` in Docker health despite serving requests on `6333`; verify functionality via API workflows.

## 6. Shutdown

```bash
make infra-down
```
