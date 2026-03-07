from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from services.api.app.auth.audit import AuditService
from services.api.app.files.service import FileService
from services.api.app.upload_and_ask.chat_backend import GroundedQueryExecutor
from services.api.app.upload_and_ask.indexing import IndexReadinessGateway
from services.api.app.upload_and_ask.models import (
    PendingUploadAndAskRecord,
    UploadAndAskCreateResult,
    UploadAndAskStatusResponse,
)
from services.api.app.upload_and_ask.repository import InMemoryPendingUploadAndAskRepository
from services.shared.enums import PendingRequestStatus, UploadAndAskScope


class UploadAndAskService:
    def __init__(
        self,
        *,
        file_service: FileService,
        repository: InMemoryPendingUploadAndAskRepository,
        index_readiness: IndexReadinessGateway,
        grounded_query_executor: GroundedQueryExecutor,
        audit_service: AuditService,
    ) -> None:
        self._file_service = file_service
        self._repository = repository
        self._index_readiness = index_readiness
        self._grounded_query_executor = grounded_query_executor
        self._audit_service = audit_service

    async def create_request(
        self,
        *,
        workspace_id: str,
        query: str,
        files: list[UploadFile],
        scope: UploadAndAskScope,
        actor_user_id: str,
    ) -> UploadAndAskCreateResult:
        if not query.strip():
            raise HTTPException(status_code=400, detail="Query is required")
        if not files:
            raise HTTPException(status_code=400, detail="At least one file is required")
        if scope != UploadAndAskScope.UPLOADED_FILES_ONLY:
            raise HTTPException(status_code=400, detail="Upload-and-ask currently supports uploaded_files_only scope")

        uploaded_file_ids: list[str] = []
        try:
            for item in files:
                payload = await item.read()
                upload_result = await self._file_service.upload(
                    workspace_id=workspace_id,
                    filename=item.filename or "upload.bin",
                    payload=payload,
                    declared_mime=item.content_type,
                    actor_user_id=actor_user_id,
                )
                uploaded_file_ids.append(upload_result.file_id)
        except Exception:
            for file_id in uploaded_file_ids:
                self._file_service.delete(
                    workspace_id=workspace_id,
                    file_id=file_id,
                    actor_user_id=actor_user_id,
                )
            raise

        now = datetime.now(tz=timezone.utc)
        record = PendingUploadAndAskRecord(
            requestId=f"req_{uuid4().hex}",
            workspaceId=workspace_id,
            query=query,
            scope=scope,
            fileIds=uploaded_file_ids,
            status=PendingRequestStatus.WAITING_FOR_INDEX,
            createdAt=now,
            updatedAt=now,
            createdBy=actor_user_id,
            citations=[],
        )
        self._repository.create(record)
        self._audit_service.record_event(
            action="upload_and_ask_requested",
            entity_type="pending_request",
            entity_id=record.request_id,
            actor_user_id=actor_user_id,
            workspace_id=workspace_id,
            metadata={"fileCount": len(uploaded_file_ids), "scope": scope.value},
        )

        return UploadAndAskCreateResult(
            requestId=record.request_id,
            status=record.status,
            message="Upload-and-ask request accepted and waiting for indexing",
        )

    def get_request(self, *, workspace_id: str, request_id: str) -> UploadAndAskStatusResponse:
        record = self._get_workspace_request(workspace_id=workspace_id, request_id=request_id)
        return self._synchronize_and_render(record)

    def _synchronize_and_render(self, record: PendingUploadAndAskRecord) -> UploadAndAskStatusResponse:
        if record.status in {
            PendingRequestStatus.WAITING_FOR_INDEX,
            PendingRequestStatus.EXECUTING,
        }:
            readiness = self._index_readiness.check(
                workspace_id=record.workspace_id,
                file_ids=record.file_ids,
            )
            if readiness.terminal_failure:
                was_failed = record.status == PendingRequestStatus.FAILED
                record = self._repository.update(
                    record.model_copy(
                        update={
                            "status": PendingRequestStatus.FAILED,
                            "error_message": "One or more files failed ingestion or were deleted",
                            "updated_at": datetime.now(tz=timezone.utc),
                        }
                    )
                )
                if not was_failed:
                    self._audit_service.record_event(
                        action="upload_and_ask_failed",
                        entity_type="pending_request",
                        entity_id=record.request_id,
                        actor_user_id=record.created_by,
                        workspace_id=record.workspace_id,
                        metadata={"reason": "required_file_terminal_failure"},
                    )
            elif readiness.all_indexed and record.status == PendingRequestStatus.WAITING_FOR_INDEX:
                executing = self._repository.update(
                    record.model_copy(
                        update={
                            "status": PendingRequestStatus.EXECUTING,
                            "updated_at": datetime.now(tz=timezone.utc),
                            "error_message": None,
                        }
                    )
                )
                try:
                    grounded = self._grounded_query_executor.ask(
                        workspace_id=executing.workspace_id,
                        query=executing.query,
                        file_ids=executing.file_ids,
                        scope=executing.scope,
                    )
                except Exception as exc:
                    record = self._repository.update(
                        executing.model_copy(
                            update={
                                "status": PendingRequestStatus.FAILED,
                                "updated_at": datetime.now(tz=timezone.utc),
                                "error_message": str(exc),
                            }
                        )
                    )
                    self._audit_service.record_event(
                        action="upload_and_ask_failed",
                        entity_type="pending_request",
                        entity_id=record.request_id,
                        actor_user_id=record.created_by,
                        workspace_id=record.workspace_id,
                        metadata={"reason": "execution_error"},
                    )
                else:
                    record = self._repository.update(
                        executing.model_copy(
                            update={
                                "status": PendingRequestStatus.COMPLETED,
                                "updated_at": datetime.now(tz=timezone.utc),
                                "answer": grounded.answer,
                                "citations": grounded.citations,
                            }
                        )
                    )
                    self._audit_service.record_event(
                        action="upload_and_ask_completed",
                        entity_type="pending_request",
                        entity_id=record.request_id,
                        actor_user_id=record.created_by,
                        workspace_id=record.workspace_id,
                        metadata={"citationCount": len(record.citations)},
                    )

        file_statuses = {
            file_id: status.value
            for file_id, status in self._index_readiness.check(
                workspace_id=record.workspace_id,
                file_ids=record.file_ids,
            ).file_statuses.items()
        }
        return UploadAndAskStatusResponse(
            requestId=record.request_id,
            workspaceId=record.workspace_id,
            status=record.status,
            scope=record.scope,
            query=record.query,
            fileIds=record.file_ids,
            fileStatuses=file_statuses,
            answer=record.answer,
            citations=record.citations,
            errorMessage=record.error_message,
            createdAt=record.created_at,
            updatedAt=record.updated_at,
        )

    def _get_workspace_request(self, *, workspace_id: str, request_id: str) -> PendingUploadAndAskRecord:
        record = self._repository.get(request_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Upload-and-ask request not found")
        if record.workspace_id != workspace_id:
            raise HTTPException(status_code=403, detail="Workspace access denied")
        return record
