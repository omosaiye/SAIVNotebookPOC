from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from .models import ChunkRecord, ParsedDocument

_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class ChunkingConfig:
    max_chars: int = 800
    overlap_chars: int = 120
    min_chunk_chars: int = 80


class ChunkingError(ValueError):
    pass


class DocumentChunker:
    def __init__(self, config: ChunkingConfig | None = None) -> None:
        self.config = config or ChunkingConfig()
        if self.config.overlap_chars >= self.config.max_chars:
            raise ChunkingError("overlap_chars must be smaller than max_chars")

    def chunk(self, document: ParsedDocument) -> list[ChunkRecord]:
        normalized_sections = [self._normalize_text(section.text) for section in document.sections]
        chunks: list[ChunkRecord] = []
        ordinal = 0

        for section_index, text in enumerate(normalized_sections):
            if not text:
                continue
            for segment_index, segment in enumerate(self._split_text(text)):
                metadata = {
                    "title": document.title,
                    "source_uri": document.source_uri,
                    "section_index": section_index,
                    "segment_index": segment_index,
                    "document_metadata": dict(document.metadata),
                }
                chunk_id = f"{document.document_id}:{ordinal}"
                chunks.append(
                    ChunkRecord(
                        chunk_id=chunk_id,
                        document_id=document.document_id,
                        tenant_id=document.tenant_id,
                        ordinal=ordinal,
                        text=segment,
                        metadata=metadata,
                    )
                )
                ordinal += 1

        return chunks

    def _split_text(self, text: str) -> Iterable[str]:
        max_chars = self.config.max_chars
        overlap = self.config.overlap_chars

        if len(text) <= max_chars:
            if len(text) >= self.config.min_chunk_chars:
                yield text
            return

        cursor = 0
        while cursor < len(text):
            end = min(len(text), cursor + max_chars)
            segment = text[cursor:end]
            if len(segment) < self.config.min_chunk_chars and end != len(text):
                cursor = end
                continue
            yield segment
            if end == len(text):
                break
            cursor = end - overlap

    @staticmethod
    def _normalize_text(text: str) -> str:
        cleaned = _WHITESPACE_RE.sub(" ", text).strip()
        return cleaned
