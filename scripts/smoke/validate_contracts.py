from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT / "packages/shared-types/contracts/enums.json"
TS_ENUMS = ROOT / "packages/shared-types/src/enums.ts"

EXPECTED = {
    "fileStatus": [
        "uploaded",
        "queued",
        "parsing",
        "OCR_fallback",
        "chunking",
        "embedding",
        "indexed",
        "failed",
        "deleting",
        "deleted",
    ],
    "pendingRequestStatus": [
        "waiting_for_index",
        "executing",
        "completed",
        "failed",
        "cancelled",
    ],
    "chatMode": ["grounded"],
    "uploadAndAskScope": ["uploaded_files_only", "workspace"],
}


def main() -> int:
    data = json.loads(CANONICAL.read_text(encoding="utf-8"))

    if data != EXPECTED:
        raise SystemExit("canonical enums JSON does not match frozen expected values")

    enums_ts = TS_ENUMS.read_text(encoding="utf-8")
    for value in EXPECTED["fileStatus"] + EXPECTED["pendingRequestStatus"] + EXPECTED["chatMode"] + EXPECTED["uploadAndAskScope"]:
        if f'"{value}"' not in enums_ts:
            raise SystemExit(f"missing enum value in TypeScript enums: {value}")

    print("contract enums validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
