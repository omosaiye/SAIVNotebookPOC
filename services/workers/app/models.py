from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class IngestionJob:
    file_id: str
    workspace_id: str
    object_key: str
    file_name: str
    mime_type: str
    size_bytes: int
    correlation_id: str | None = None
    requested_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class ParsedChunk:
    text: str
    ordinal: int
    page: int | None = None
    sheet_name: str | None = None
    section_heading: str | None = None
    token_estimate: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ParsedDocument:
    parser_used: str
    content_type: str
    raw_text: str
    chunks: list[ParsedChunk]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ChunkHandoffRecord:
    chunk_id: str
    file_id: str
    workspace_id: str
    ordinal: int
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
