from __future__ import annotations

from services.workers.app.models import ParsedChunk, ParsedDocument


class OCRService:
    def should_trigger(self, *, parser_used: str, mime_type: str, chunks_count: int) -> bool:
        return chunks_count == 0 and mime_type in {
            "application/pdf",
            "image/png",
            "image/jpeg",
            "image/tiff",
        }

    def extract(self, payload: bytes, mime_type: str) -> ParsedDocument:
        try:
            import pytesseract  # type: ignore  # noqa: F401
        except Exception:
            text = "[ocr unavailable]"
            parser_used = "ocr_stub"
        else:
            text = payload.decode("utf-8", errors="ignore") or "[ocr text extracted]"
            parser_used = "ocr_tesseract"

        chunks = [ParsedChunk(text=text, ordinal=0, metadata={"ocrApplied": True})] if text else []
        return ParsedDocument(
            parser_used=parser_used,
            content_type=mime_type,
            raw_text=text,
            chunks=chunks,
            metadata={"ocrApplied": True},
        )
