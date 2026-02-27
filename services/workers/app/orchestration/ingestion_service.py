from __future__ import annotations

from celery.exceptions import Retry

from services.shared.enums import FileStatus
from services.workers.app.models import IngestionJob
from services.workers.app.parsers.base import ParseRequest
from services.workers.app.parsers.docling_service import DoclingFirstParserService
from services.workers.app.parsers.ocr_service import OCRService
from services.workers.app.persistence.repository import IngestionPersistenceRepository
from services.workers.app.storage.object_store import ObjectStoreClient


class IngestionOrchestrationService:
    def __init__(
        self,
        *,
        repository: IngestionPersistenceRepository,
        parser: DoclingFirstParserService,
        ocr_service: OCRService,
        object_store: ObjectStoreClient,
    ) -> None:
        self._repository = repository
        self._parser = parser
        self._ocr_service = ocr_service
        self._object_store = object_store

    def run(self, job: IngestionJob) -> dict:
        self._repository.create_document(job)
        self._repository.update_document_status(job.file_id, status=FileStatus.PARSING)
        payload = self._object_store.get_bytes(job.object_key)

        parse_request = ParseRequest(
            file_name=job.file_name, mime_type=job.mime_type, payload=payload
        )
        parsed = self._parser.parse(parse_request)

        if self._ocr_service.should_trigger(
            parser_used=parsed.parser_used,
            mime_type=job.mime_type,
            chunks_count=len(parsed.chunks),
        ):
            self._repository.update_document_status(job.file_id, status=FileStatus.OCR_FALLBACK)
            self._repository.record_event(
                job.file_id, "ocr_fallback_triggered", {"reason": "empty_parse_output"}
            )
            parsed = self._ocr_service.extract(payload, job.mime_type)

        self._repository.update_document_status(
            job.file_id,
            status=FileStatus.CHUNKING,
            parser_used=parsed.parser_used,
            raw_text=parsed.raw_text,
            metadata=parsed.metadata,
        )
        chunk_records = self._repository.store_parsed_output(job, parsed)

        handoff = {
            "fileId": job.file_id,
            "workspaceId": job.workspace_id,
            "status": FileStatus.CHUNKING.value,
            "parserUsed": parsed.parser_used,
            "chunkCount": len(chunk_records),
            "chunks": [
                {
                    "chunkId": record.chunk_id,
                    "ordinal": record.ordinal,
                    "text": record.text,
                    "metadata": record.metadata,
                }
                for record in chunk_records
            ],
        }
        self._repository.record_event(
            job.file_id, "chunking_handoff_ready", {"chunkCount": len(chunk_records)}
        )
        return handoff


def map_retryable_failure(exc: Exception) -> bool:
    return isinstance(exc, (ConnectionError, TimeoutError, Retry))
