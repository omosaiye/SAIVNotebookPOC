from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
import psycopg

from services.api.app.files.models import ListFilesFilters
from services.api.app.files.repository import FileRepository
from services.shared.embedding import cosine_similarity, deterministic_embedding
from services.shared.enums import FileStatus, UploadAndAskScope


@dataclass
class RetrievedChunk:
    chunk_id: str
    file_id: str
    file_name: str
    text: str
    score: float
    page: int | None = None
    sheet_name: str | None = None
    section_heading: str | None = None


class RetrievalService:
    def retrieve(
        self,
        *,
        workspace_id: str,
        query: str,
        scope: UploadAndAskScope,
        file_ids: list[str],
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        raise NotImplementedError


class FileBackedRetrievalService(RetrievalService):
    def __init__(self, *, file_repository: FileRepository) -> None:
        self._file_repository = file_repository

    def retrieve(
        self,
        *,
        workspace_id: str,
        query: str,
        scope: UploadAndAskScope,
        file_ids: list[str],
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        if scope == UploadAndAskScope.UPLOADED_FILES_ONLY and not file_ids:
            raise HTTPException(status_code=400, detail="fileIds are required for uploaded_files_only scope")

        candidates = []
        if file_ids:
            for file_id in file_ids:
                row = self._file_repository.get(file_id)
                if row is None:
                    raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
                if row.workspace_id != workspace_id:
                    raise HTTPException(status_code=403, detail="Workspace access denied")
                candidates.append(row)
        else:
            candidates = self._file_repository.list(
                ListFilesFilters(
                    workspace_id=workspace_id,
                    status=None,
                    search=None,
                    include_deleted=False,
                )
            )

        indexed = [row for row in candidates if row.status == FileStatus.INDEXED]
        chunks: list[RetrievedChunk] = []
        for row in indexed[:top_k]:
            chunks.append(
                RetrievedChunk(
                    chunk_id=f"{row.id}:chunk:0",
                    file_id=row.id,
                    file_name=row.file_name,
                    text=f"Indexed context from {row.file_name} relevant to: {query}",
                    score=0.65,
                )
            )
        return chunks


class PostgresIndexedRetrievalService(RetrievalService):
    def __init__(
        self,
        *,
        database_url: str,
        fallback: RetrievalService,
    ) -> None:
        self._database_url = database_url
        self._fallback = fallback

    def retrieve(
        self,
        *,
        workspace_id: str,
        query: str,
        scope: UploadAndAskScope,
        file_ids: list[str],
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        if scope == UploadAndAskScope.UPLOADED_FILES_ONLY and not file_ids:
            raise HTTPException(status_code=400, detail="fileIds are required for uploaded_files_only scope")

        try:
            candidates = self._fetch_candidates(
                workspace_id=workspace_id,
                file_ids=file_ids,
            )
        except Exception:
            return self._fallback.retrieve(
                workspace_id=workspace_id,
                query=query,
                scope=scope,
                file_ids=file_ids,
                top_k=top_k,
            )

        if not candidates:
            return self._fallback.retrieve(
                workspace_id=workspace_id,
                query=query,
                scope=scope,
                file_ids=file_ids,
                top_k=top_k,
            )

        query_vector = deterministic_embedding(query)
        scored: list[tuple[float, dict[str, Any]]] = []
        for row in candidates:
            embedding_values = row.get("embedding_values")
            if not isinstance(embedding_values, list) or not embedding_values:
                continue
            score = cosine_similarity(query_vector, [float(value) for value in embedding_values])
            scored.append((score, row))

        if not scored:
            return self._fallback.retrieve(
                workspace_id=workspace_id,
                query=query,
                scope=scope,
                file_ids=file_ids,
                top_k=top_k,
            )

        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            RetrievedChunk(
                chunk_id=row["chunk_id"],
                file_id=row["file_id"],
                file_name=row["file_name"],
                text=row["text_content"],
                score=score,
                page=row.get("page"),
                sheet_name=row.get("sheet_name"),
                section_heading=row.get("section_heading"),
            )
            for score, row in scored[:top_k]
        ]

    def _fetch_candidates(
        self,
        *,
        workspace_id: str,
        file_ids: list[str],
    ) -> list[dict[str, Any]]:
        query = """
            SELECT
                c.id AS chunk_id,
                c.file_id,
                d.file_name,
                c.text_content,
                c.page,
                c.sheet_name,
                c.section_heading,
                c.embedding_json
            FROM ingestion_chunks c
            JOIN ingestion_documents d ON d.file_id = c.file_id
            WHERE c.workspace_id = %s
              AND d.status = %s
        """
        params: list[Any] = [workspace_id, FileStatus.INDEXED.value]

        if file_ids:
            query += " AND c.file_id = ANY(%s)"
            params.append(file_ids)

        query += " ORDER BY c.created_at DESC LIMIT 400"

        with psycopg.connect(self._database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()

        results: list[dict[str, Any]] = []
        for row in rows:
            embedding_json = row[7]
            values = None
            if isinstance(embedding_json, dict):
                candidate = embedding_json.get("values")
                if isinstance(candidate, list):
                    values = candidate
            results.append(
                {
                    "chunk_id": row[0],
                    "file_id": row[1],
                    "file_name": row[2],
                    "text_content": row[3],
                    "page": row[4],
                    "sheet_name": row[5],
                    "section_heading": row[6],
                    "embedding_values": values,
                }
            )
        return results
