from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException

from services.api.app.auth.audit import AuditService
from services.api.app.files.models import FileRecord, ListFilesFilters
from services.api.app.files.queue import IngestionQueue
from services.api.app.files.repository import InMemoryFileRepository
from services.api.app.files.signature import FileValidationError, validate_file_type
from services.api.app.files.storage import ObjectStorage
from services.shared.contracts import FileDetail, FileSummary, UploadResponse
from services.shared.enums import FileStatus


class FileService:
    def __init__(
        self,
        *,
        repository: InMemoryFileRepository,
        storage: ObjectStorage,
        ingestion_queue: IngestionQueue,
        max_file_size_bytes: int,
        audit_service: AuditService,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._ingestion_queue = ingestion_queue
        self._max_file_size_bytes = max_file_size_bytes
        self._audit_service = audit_service

    async def upload(
        self,
        *,
        workspace_id: str,
        filename: str,
        payload: bytes,
        declared_mime: str | None,
        actor_user_id: str | None = None,
    ) -> UploadResponse:
        if not payload:
            raise HTTPException(status_code=400, detail="File is empty")
        if len(payload) > self._max_file_size_bytes:
            raise HTTPException(status_code=413, detail="File size exceeds configured limit")

        try:
            mime_type = validate_file_type(filename, payload, declared_mime)
        except FileValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        file_id = f"file_{uuid4().hex}"
        object_key = f"{workspace_id}/{file_id}/{filename}"

        record = FileRecord(
            id=file_id,
            workspace_id=workspace_id,
            file_name=filename,
            status=FileStatus.UPLOADED,
            uploaded_at=datetime.now(tz=timezone.utc),
            mime_type=mime_type,
            size_bytes=len(payload),
            object_key=object_key,
        )
        self._repository.create(record)
        self._storage.put(object_key=object_key, payload=payload)

        queued = self._repository.transition_status(record, FileStatus.QUEUED)
        self._ingestion_queue.enqueue(file_id=queued.id, workspace_id=workspace_id)
        self._audit_service.record_event(
            action="file_uploaded",
            entity_type="file",
            entity_id=queued.id,
            actor_user_id=actor_user_id,
            workspace_id=workspace_id,
            metadata={
                "fileName": filename,
                "mimeType": mime_type,
                "sizeBytes": len(payload),
                "status": queued.status.value,
            },
        )

        return UploadResponse(
            fileId=queued.id,
            status=queued.status,
            message="File accepted for processing",
        )

    def list_files(
        self,
        *,
        workspace_id: str,
        status: FileStatus | None,
        search: str | None,
        include_deleted: bool,
    ) -> list[FileSummary]:
        rows = self._repository.list(
            ListFilesFilters(
                workspace_id=workspace_id,
                status=status,
                search=search,
                include_deleted=include_deleted,
            )
        )
        return [
            FileSummary(
                id=row.id,
                workspaceId=row.workspace_id,
                fileName=row.file_name,
                status=row.status,
                uploadedAt=row.uploaded_at,
            )
            for row in rows
        ]

    def get_file(self, *, workspace_id: str, file_id: str) -> FileDetail:
        row = self._get_workspace_file(workspace_id=workspace_id, file_id=file_id)
        return FileDetail(
            id=row.id,
            workspaceId=row.workspace_id,
            fileName=row.file_name,
            status=row.status,
            uploadedAt=row.uploaded_at,
            mimeType=row.mime_type,
            sizeBytes=row.size_bytes,
            objectKey=row.object_key,
            parserUsed=row.parser_used,
            errorMessage=row.error_message,
        )

    def reprocess(
        self,
        *,
        workspace_id: str,
        file_id: str,
        actor_user_id: str | None = None,
    ) -> UploadResponse:
        row = self._get_workspace_file(workspace_id=workspace_id, file_id=file_id)
        if row.status == FileStatus.DELETED:
            raise HTTPException(status_code=409, detail="Cannot reprocess a deleted file")

        replacement = self._repository.transition_status(row, FileStatus.QUEUED, error_message=None)
        self._ingestion_queue.enqueue(file_id=replacement.id, workspace_id=workspace_id)
        self._audit_service.record_event(
            action="file_reprocess_requested",
            entity_type="file",
            entity_id=replacement.id,
            actor_user_id=actor_user_id,
            workspace_id=workspace_id,
            metadata={"status": replacement.status.value},
        )

        return UploadResponse(
            fileId=replacement.id,
            status=replacement.status,
            message="File reprocess accepted and re-queued",
        )

    def delete(
        self,
        *,
        workspace_id: str,
        file_id: str,
        actor_user_id: str | None = None,
    ) -> UploadResponse:
        row = self._get_workspace_file(workspace_id=workspace_id, file_id=file_id)
        tombstone = self._repository.transition_status(row, FileStatus.DELETING)
        self._storage.delete(object_key=tombstone.object_key)
        deleted = self._repository.transition_status(tombstone, FileStatus.DELETED)
        self._audit_service.record_event(
            action="file_deleted",
            entity_type="file",
            entity_id=deleted.id,
            actor_user_id=actor_user_id,
            workspace_id=workspace_id,
            metadata={"status": deleted.status.value},
        )

        return UploadResponse(fileId=deleted.id, status=deleted.status, message="File deleted")

    def _get_workspace_file(self, *, workspace_id: str, file_id: str) -> FileRecord:
        row = self._repository.get(file_id)
        if row is None:
            raise HTTPException(status_code=404, detail="File not found")
        if row.workspace_id != workspace_id:
            raise HTTPException(status_code=403, detail="Workspace access denied")
        return row
