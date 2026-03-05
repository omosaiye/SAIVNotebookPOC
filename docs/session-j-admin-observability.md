# Session J: Admin, Observability, and Resilience Notes

## Delivered surfaces

- Admin settings API and web page (`/admin`) for runtime model/chunking controls.
- Admin ingestion visibility endpoints for job state, logs, and stage timing metrics.
- Golden corpus fixture bundle and one-command upload loader.
- End-to-end API tests covering ingestion/query and upload-and-ask lifecycle.

## Retryable failures

Worker task `ingestion.process_file` retries transient failures via Celery autoretry:

- retryable exception classes:
  - `ConnectionError`
  - `TimeoutError`
  - `celery.exceptions.Retry`
- retry policy:
  - max retries: `3`
  - initial countdown: `5s`
  - backoff enabled

Non-retryable failures mark processing as failed and are visible through file status and admin logs.

## Idempotency safeguards

- `ingestion_documents` uses `file_id` as the primary key.
- Worker document creation uses upsert semantics (`ON CONFLICT ... DO UPDATE`).
- Parsed chunks are replaced per file by deleting prior rows before reinsert.
- Chunk IDs are deterministic (`{file_id}:chunk:{ordinal}`), avoiding duplicate fanout IDs on rerun.
- Reprocess endpoint re-queues existing files safely and resets error state.

## Golden corpus

Fixture source: `tests/fixtures/golden/input`

- `employee_handbook.txt`
- `security_controls.csv`
- `invoice_summary.txt`
- `faq.md`

Loader command:

```bash
./scripts/fixtures/load_golden_corpus.sh
```

Optional environment overrides:

- `API_BASE_URL`
- `AUTH_EMAIL`
- `AUTH_PASSWORD`
- `WORKSPACE_ID`

## End-to-end test suite

Run:

```bash
.venv/bin/pytest -q services/api/tests/test_e2e_workflows.py services/api/tests/test_admin_api.py
```

Coverage:

- upload -> indexed transition -> grounded query with citations
- upload-and-ask request lifecycle to completion
- admin settings read/update validation
- admin job/log/metrics visibility checks
