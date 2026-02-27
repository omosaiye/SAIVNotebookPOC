from __future__ import annotations

import sqlite3
import uuid
from typing import Iterable

from .models import ChunkRecord, IndexingRun, IndexingStatus, utc_now_iso


class IndexingPersistence:
    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._initialize()

    def _connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS indexing_runs (
                    run_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS indexed_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    ordinal INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES indexing_runs(run_id)
                );
                """
            )

    def create_run(self, document_id: str, tenant_id: str) -> IndexingRun:
        now = utc_now_iso()
        run_id = str(uuid.uuid4())
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO indexing_runs(run_id, document_id, tenant_id, status, error_message, created_at, updated_at) VALUES (?, ?, ?, ?, NULL, ?, ?)",
                (run_id, document_id, tenant_id, IndexingStatus.PENDING.value, now, now),
            )
        return self.get_run(run_id)

    def update_status(self, run_id: str, status: IndexingStatus, error_message: str | None = None) -> IndexingRun:
        now = utc_now_iso()
        with self._connection() as conn:
            conn.execute(
                "UPDATE indexing_runs SET status = ?, error_message = ?, updated_at = ? WHERE run_id = ?",
                (status.value, error_message, now, run_id),
            )
        return self.get_run(run_id)

    def persist_chunks(self, run_id: str, chunks: Iterable[ChunkRecord]) -> None:
        import json

        with self._connection() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO indexed_chunks(chunk_id, run_id, document_id, tenant_id, ordinal, text, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chunk.chunk_id,
                        run_id,
                        chunk.document_id,
                        chunk.tenant_id,
                        chunk.ordinal,
                        chunk.text,
                        json.dumps(dict(chunk.metadata), sort_keys=True),
                    )
                    for chunk in chunks
                ],
            )

    def get_run(self, run_id: str) -> IndexingRun:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM indexing_runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        return IndexingRun(
            run_id=row["run_id"],
            document_id=row["document_id"],
            tenant_id=row["tenant_id"],
            status=IndexingStatus(row["status"]),
            error_message=row["error_message"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def list_chunks_for_document(self, document_id: str) -> list[dict[str, str]]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT chunk_id, text, metadata_json FROM indexed_chunks WHERE document_id = ? ORDER BY ordinal ASC",
                (document_id,),
            ).fetchall()
        return [dict(row) for row in rows]
