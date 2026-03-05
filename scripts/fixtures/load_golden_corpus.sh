#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GOLDEN_DIR="${ROOT_DIR}/tests/fixtures/golden/input"

API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
AUTH_EMAIL="${AUTH_EMAIL:-owner@local.dev}"
AUTH_PASSWORD="${AUTH_PASSWORD:-dev-password}"
WORKSPACE_ID="${WORKSPACE_ID:-ws_1}"

if [ ! -d "${GOLDEN_DIR}" ]; then
  echo "golden fixture directory not found: ${GOLDEN_DIR}" >&2
  exit 1
fi

login_payload="$(printf '{"email":"%s","password":"%s"}' "${AUTH_EMAIL}" "${AUTH_PASSWORD}")"
login_response="$(curl -sS -X POST "${API_BASE_URL}/api/v1/auth/login" -H "Content-Type: application/json" -d "${login_payload}")"
token="$(printf "%s" "${login_response}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["accessToken"])')"

upload_one() {
  local path="$1"
  local filename
  filename="$(basename "${path}")"

  local mime_type
  mime_type="$(file --brief --mime-type "${path}" 2>/dev/null || true)"
  if [ -z "${mime_type}" ]; then
    mime_type="application/octet-stream"
  fi

  curl -sS -X POST "${API_BASE_URL}/api/v1/files/upload" \
    -H "Authorization: Bearer ${token}" \
    -H "X-Workspace-Id: ${WORKSPACE_ID}" \
    -H "X-File-Name: ${filename}" \
    -H "Content-Type: ${mime_type}" \
    --data-binary "@${path}" >/dev/null

  echo "uploaded ${filename}"
}

for fixture in "${GOLDEN_DIR}"/*; do
  if [ -f "${fixture}" ]; then
    upload_one "${fixture}"
  fi
done

echo "golden corpus upload complete"
