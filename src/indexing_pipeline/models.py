from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class IndexingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


@dataclass(frozen=True)
class ParsedSection:
    """Canonical parsed document section from Session D ingestion output."""

    text: str
    section_name: str | None = None
    start_page: int | None = None
    end_page: int | None = None
    source_offset: int | None = None


@dataclass(frozen=True)
class ParsedDocument:
    """Input contract for chunking; expected to be supplied by Session D."""

    document_id: str
    tenant_id: str
    source_uri: str
    title: str
    sections: tuple[ParsedSection, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ChunkRecord:
    """Normalized retrieval-ready chunk representation."""

    chunk_id: str
    document_id: str
    tenant_id: str
    ordinal: int
    text: str
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class EmbeddingVector:
    chunk_id: str
    values: tuple[float, ...]
    model_name: str


@dataclass(frozen=True)
class IndexingRun:
    run_id: str
    document_id: str
    tenant_id: str
    status: IndexingStatus
    error_message: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    score: float
    document_id: str
    tenant_id: str
    text: str
    metadata: Mapping[str, Any]
