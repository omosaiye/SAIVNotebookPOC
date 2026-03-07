from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path

_CANONICAL_ENUMS_PATH = Path(__file__).resolve().parents[2] / "packages/shared-types/contracts/enums.json"


class FileStatus(StrEnum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PARSING = "parsing"
    OCR_FALLBACK = "OCR_fallback"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXED = "indexed"
    FAILED = "failed"
    DELETING = "deleting"
    DELETED = "deleted"


class PendingRequestStatus(StrEnum):
    WAITING_FOR_INDEX = "waiting_for_index"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ChatMode(StrEnum):
    GROUNDED = "grounded"


class UploadAndAskScope(StrEnum):
    UPLOADED_FILES_ONLY = "uploaded_files_only"
    WORKSPACE = "workspace"


def load_canonical_enums() -> dict[str, list[str]]:
    with _CANONICAL_ENUMS_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _enum_values(enum_class: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_class]


def validate_enum_alignment() -> None:
    canonical = load_canonical_enums()
    comparisons = {
        "fileStatus": _enum_values(FileStatus),
        "pendingRequestStatus": _enum_values(PendingRequestStatus),
        "chatMode": _enum_values(ChatMode),
        "uploadAndAskScope": _enum_values(UploadAndAskScope),
    }

    mismatches = [
        key
        for key, values in comparisons.items()
        if canonical.get(key) != values
    ]
    if mismatches:
        raise RuntimeError(
            "Canonical enum mismatch for keys: " + ", ".join(mismatches)
        )


validate_enum_alignment()
