from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException

from services.api.app.files.models import ListFilesFilters
from services.api.app.files.repository import InMemoryFileRepository
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
    def __init__(self, *, file_repository: InMemoryFileRepository) -> None:
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

