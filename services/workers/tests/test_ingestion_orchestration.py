from __future__ import annotations

from pathlib import Path

from services.workers.app.indexing.service import ChunkIndexingService
from services.workers.app.models import IngestionJob
from services.workers.app.orchestration.ingestion_service import IngestionOrchestrationService
from services.workers.app.parsers.docling_service import DoclingFirstParserService
from services.workers.app.parsers.ocr_service import OCRService
from services.workers.app.persistence.repository import InMemoryIngestionRepository
from services.workers.app.storage.object_store import ObjectStoreClient


def test_ingestion_orchestration_generates_chunk_handoff(tmp_path: Path) -> None:
    sample = tmp_path / "sample.txt"
    sample.write_text("hello worker ingestion")

    repository = InMemoryIngestionRepository()
    service = IngestionOrchestrationService(
        repository=repository,
        parser=DoclingFirstParserService(),
        ocr_service=OCRService(),
        object_store=ObjectStoreClient(),
        indexer=ChunkIndexingService(
            repository=repository,
            embedding_model_name="deterministic-hash-v1",
        ),
    )

    result = service.run(
        IngestionJob(
            file_id="file-1",
            workspace_id="ws-1",
            object_key=str(sample),
            file_name="sample.txt",
            mime_type="text/plain",
            size_bytes=sample.stat().st_size,
        )
    )

    assert result["status"] == "indexed"
    assert result["chunkCount"] == 1
    assert result["vectorCount"] == 1
    assert result["chunks"][0]["text"].startswith("hello")
    assert repository.embeddings["file-1"]


def test_ocr_fallback_triggers_for_empty_pdf(tmp_path: Path) -> None:
    sample = tmp_path / "empty.pdf"
    sample.write_bytes(b"")

    repository = InMemoryIngestionRepository()
    service = IngestionOrchestrationService(
        repository=repository,
        parser=DoclingFirstParserService(),
        ocr_service=OCRService(),
        object_store=ObjectStoreClient(),
        indexer=ChunkIndexingService(
            repository=repository,
            embedding_model_name="deterministic-hash-v1",
        ),
    )

    result = service.run(
        IngestionJob(
            file_id="file-2",
            workspace_id="ws-2",
            object_key=str(sample),
            file_name="empty.pdf",
            mime_type="application/pdf",
            size_bytes=0,
        )
    )

    assert result["parserUsed"] in {"ocr_stub", "ocr_tesseract"}
    assert any(event["event_name"] == "ocr_fallback_triggered" for event in repository.events)
    assert result["status"] == "indexed"
