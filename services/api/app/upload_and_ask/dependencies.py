from __future__ import annotations

from services.api.app.auth.dependencies import get_audit_service
from services.api.app.files.dependencies import get_file_repository, get_file_service
from services.api.app.upload_and_ask.chat_backend import StubGroundedQueryExecutor
from services.api.app.upload_and_ask.indexing import FileRepositoryIndexReadinessGateway
from services.api.app.upload_and_ask.repository import InMemoryPendingUploadAndAskRepository
from services.api.app.upload_and_ask.service import UploadAndAskService

_PENDING_REPOSITORY = InMemoryPendingUploadAndAskRepository()
_QUERY_EXECUTOR = StubGroundedQueryExecutor()


def get_upload_and_ask_service() -> UploadAndAskService:
    file_repository = get_file_repository()
    return UploadAndAskService(
        file_service=get_file_service(),
        repository=_PENDING_REPOSITORY,
        index_readiness=FileRepositoryIndexReadinessGateway(file_repository=file_repository),
        grounded_query_executor=_QUERY_EXECUTOR,
        audit_service=get_audit_service(),
    )


def reset_upload_and_ask_dependencies() -> None:
    _PENDING_REPOSITORY.clear()
