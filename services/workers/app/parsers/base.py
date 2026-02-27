from __future__ import annotations

from dataclasses import dataclass

from services.workers.app.models import ParsedDocument


@dataclass(slots=True)
class ParseRequest:
    file_name: str
    mime_type: str
    payload: bytes


class ParserService:
    def parse(self, request: ParseRequest) -> ParsedDocument:
        raise NotImplementedError
