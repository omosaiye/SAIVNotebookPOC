# Golden Corpus (Session J)

This corpus is used for deterministic integration checks and local demo loading.

## Files

- `employee_handbook.txt`: native text sample for plain-text ingestion.
- `security_controls.csv`: tabular sample for structured CSV extraction.
- `invoice_summary.txt`: short finance-like narrative for retrieval and citation checks.
- `faq.md`: markdown sample for heading-aware chunking behavior.

## Usage

1. Start API/worker infrastructure.
2. Run `./scripts/fixtures/load_golden_corpus.sh`.
3. Verify file statuses in the web app (`/workspace`) and admin panel (`/admin`).
