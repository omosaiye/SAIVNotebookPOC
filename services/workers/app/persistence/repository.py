from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from services.shared.enums import FileStatus
from services.workers.app.models import ChunkHandoffRecord, IngestionJob, ParsedDocument


@dataclass(slots=True)
class IngestionPersistenceRepository:
    database_url: str

    @contextmanager
    def _connection(self) -> Iterator[object]:
        import psycopg

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cursor:
                self._ensure_tables(cursor)
            conn.commit()
            yield conn

    def _ensure_tables(self, cursor: object) -> None:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ingestion_documents (
                file_id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                object_key TEXT NOT NULL,
                size_bytes BIGINT NOT NULL,
                parser_used TEXT,
                status TEXT NOT NULL,
                raw_text TEXT,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                error_message TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ingestion_chunks (
                id TEXT PRIMARY KEY,
                file_id TEXT NOT NULL REFERENCES ingestion_documents(file_id) ON DELETE CASCADE,
                workspace_id TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                text_content TEXT NOT NULL,
                page INTEGER,
                sheet_name TEXT,
                section_heading TEXT,
                token_estimate INTEGER,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ingestion_events (
                id BIGSERIAL PRIMARY KEY,
                file_id TEXT NOT NULL,
                event_name TEXT NOT NULL,
                event_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )

    def create_document(self, job: IngestionJob) -> None:
        with self._connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO ingestion_documents
                    (file_id, workspace_id, file_name, mime_type, object_key, size_bytes, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (file_id)
                    DO UPDATE SET
                        workspace_id = EXCLUDED.workspace_id,
                        file_name = EXCLUDED.file_name,
                        mime_type = EXCLUDED.mime_type,
                        object_key = EXCLUDED.object_key,
                        size_bytes = EXCLUDED.size_bytes,
                        updated_at = NOW()
                    """,
                    (
                        job.file_id,
                        job.workspace_id,
                        job.file_name,
                        job.mime_type,
                        job.object_key,
                        job.size_bytes,
                        FileStatus.QUEUED.value,
                    ),
                )
            conn.commit()

    def update_document_status(
        self,
        file_id: str,
        *,
        status: FileStatus,
        parser_used: str | None = None,
        raw_text: str | None = None,
        metadata: dict | None = None,
        error_message: str | None = None,
    ) -> None:
        with self._connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE ingestion_documents
                    SET status = %s,
                        parser_used = COALESCE(%s, parser_used),
                        raw_text = COALESCE(%s, raw_text),
                        metadata = CASE
                            WHEN %s::jsonb = '{}'::jsonb THEN metadata
                            ELSE %s::jsonb
                        END,
                        error_message = %s,
                        updated_at = NOW()
                    WHERE file_id = %s
                    """,
                    (
                        status.value,
                        parser_used,
                        raw_text,
                        json.dumps(metadata or {}),
                        json.dumps(metadata or {}),
                        error_message,
                        file_id,
                    ),
                )
            conn.commit()

    def store_parsed_output(
        self, job: IngestionJob, parsed: ParsedDocument
    ) -> list[ChunkHandoffRecord]:
        handoff_records: list[ChunkHandoffRecord] = []
        with self._connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM ingestion_chunks WHERE file_id = %s", (job.file_id,))
                for chunk in parsed.chunks:
                    chunk_id = f"{job.file_id}:chunk:{chunk.ordinal}"
                    cursor.execute(
                        """
                        INSERT INTO ingestion_chunks
                        (
                            id,
                            file_id,
                            workspace_id,
                            ordinal,
                            text_content,
                            page,
                            sheet_name,
                            section_heading,
                            token_estimate,
                            metadata
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                        """,
                        (
                            chunk_id,
                            job.file_id,
                            job.workspace_id,
                            chunk.ordinal,
                            chunk.text,
                            chunk.page,
                            chunk.sheet_name,
                            chunk.section_heading,
                            chunk.token_estimate,
                            json.dumps(chunk.metadata),
                        ),
                    )
                    handoff_records.append(
                        ChunkHandoffRecord(
                            chunk_id=chunk_id,
                            file_id=job.file_id,
                            workspace_id=job.workspace_id,
                            ordinal=chunk.ordinal,
                            text=chunk.text,
                            metadata={
                                "page": chunk.page,
                                "sheetName": chunk.sheet_name,
                                "sectionHeading": chunk.section_heading,
                                "tokenEstimate": chunk.token_estimate,
                                **chunk.metadata,
                            },
                        )
                    )
                cursor.execute(
                    """
                    INSERT INTO ingestion_events (file_id, event_name, event_metadata)
                    VALUES (%s, %s, %s::jsonb)
                    """,
                    (
                        job.file_id,
                        "parsed_output_persisted",
                        json.dumps(
                            {"chunkCount": len(handoff_records), "parserUsed": parsed.parser_used}
                        ),
                    ),
                )
            conn.commit()
        return handoff_records

    def record_event(self, file_id: str, event_name: str, metadata: dict | None = None) -> None:
        with self._connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    (
                        "INSERT INTO ingestion_events "
                        "(file_id, event_name, event_metadata) VALUES (%s, %s, %s::jsonb)"
                    ),
                    (file_id, event_name, json.dumps(metadata or {})),
                )
            conn.commit()


class InMemoryIngestionRepository:
    def __init__(self) -> None:
        self.documents: dict[str, dict] = {}
        self.events: list[dict] = []
        self.chunks: dict[str, list[ChunkHandoffRecord]] = {}

    def create_document(self, job: IngestionJob) -> None:
        self.documents[job.file_id] = {"status": FileStatus.QUEUED.value, "job": job}

    def update_document_status(self, file_id: str, **kwargs: object) -> None:
        if file_id not in self.documents:
            self.documents[file_id] = {}
        self.documents[file_id].update(kwargs)
        if "status" in kwargs and isinstance(kwargs["status"], FileStatus):
            self.documents[file_id]["status"] = kwargs["status"].value

    def store_parsed_output(
        self, job: IngestionJob, parsed: ParsedDocument
    ) -> list[ChunkHandoffRecord]:
        result = [
            ChunkHandoffRecord(
                chunk_id=f"{job.file_id}:chunk:{chunk.ordinal}",
                file_id=job.file_id,
                workspace_id=job.workspace_id,
                ordinal=chunk.ordinal,
                text=chunk.text,
                metadata={"sheetName": chunk.sheet_name, **chunk.metadata},
            )
            for chunk in parsed.chunks
        ]
        self.chunks[job.file_id] = result
        return result

    def record_event(self, file_id: str, event_name: str, metadata: dict | None = None) -> None:
        self.events.append(
            {"file_id": file_id, "event_name": event_name, "metadata": metadata or {}}
        )
