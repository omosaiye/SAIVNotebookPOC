from __future__ import annotations

from pathlib import Path

ALLOWED_TYPES: dict[str, set[str]] = {
    "application/pdf": {".pdf"},
    "text/plain": {".txt", ".md"},
    "text/csv": {".csv"},
    "application/json": {".json"},
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {".docx"},
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {".xlsx"},
    "image/png": {".png"},
    "image/jpeg": {".jpg", ".jpeg"},
}


MAGIC_SIGNATURES: list[tuple[bytes, str]] = [
    (b"%PDF-", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"PK\x03\x04", "application/zip"),
]


class FileValidationError(ValueError):
    pass


def detect_mime(filename: str, payload: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    for signature, mime in MAGIC_SIGNATURES:
        if payload.startswith(signature):
            if mime == "application/zip":
                if suffix == ".docx":
                    return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                if suffix == ".xlsx":
                    return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            return mime

    if suffix in {".txt", ".md"}:
        return "text/plain"
    if suffix == ".csv":
        return "text/csv"
    if suffix == ".json":
        return "application/json"

    raise FileValidationError("Unsupported file type or unknown signature")


def validate_file_type(filename: str, payload: bytes, declared_mime: str | None) -> str:
    detected_mime = detect_mime(filename=filename, payload=payload)

    allowed_extensions = ALLOWED_TYPES.get(detected_mime)
    suffix = Path(filename).suffix.lower()
    if not allowed_extensions or suffix not in allowed_extensions:
        raise FileValidationError("File extension does not match detected signature")

    if declared_mime and declared_mime != detected_mime:
        raise FileValidationError("Declared content type does not match file signature")

    return detected_mime
