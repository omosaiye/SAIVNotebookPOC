#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

required=(
  "apps/web/.env.example"
  "services/api/.env.example"
  "services/workers/.env.example"
  "infra/docker/docker-compose.yml"
  "packages/shared-types/contracts/enums.json"
)

for file in "${required[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "missing required file: $file"
    exit 1
  fi
done

python3 scripts/smoke/validate_contracts.py
python3 -m compileall services >/dev/null

docker compose -f infra/docker/docker-compose.yml config >/dev/null

echo "startup smoke checks passed"
