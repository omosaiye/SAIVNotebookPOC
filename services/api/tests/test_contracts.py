from __future__ import annotations

from datetime import datetime, timezone

from services.shared.contracts import ChatQueryRequest, CitationResponse, FileSummary, PendingUploadAndAskRequestState
from services.shared.enums import ChatMode, FileStatus, PendingRequestStatus, UploadAndAskScope


def test_file_summary_serializes_in_contract_shape() -> None:
    model = FileSummary(
        id="file_123",
        workspaceId="ws_1",
        fileName="vendor_contract.pdf",
        status=FileStatus.UPLOADED,
        uploadedAt=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    payload = model.model_dump(by_alias=True)
    assert payload["workspaceId"] == "ws_1"
    assert payload["status"] == "uploaded"


def test_chat_query_request_and_pending_state_contracts() -> None:
    request = ChatQueryRequest(
        workspaceId="ws_1",
        chatSessionId="chat_1",
        mode=ChatMode.GROUNDED,
        query="What are the payment terms?",
        scope=UploadAndAskScope.WORKSPACE,
        fileIds=["file_123"],
    )

    pending = PendingUploadAndAskRequestState(
        requestId="req_1",
        workspaceId="ws_1",
        status=PendingRequestStatus.WAITING_FOR_INDEX,
        scope=UploadAndAskScope.UPLOADED_FILES_ONLY,
        query=request.query,
        fileIds=request.file_ids,
        createdAt=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updatedAt=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    citation = CitationResponse(
        fileId="file_123",
        fileName="vendor_contract.pdf",
        page=8,
        sheetName=None,
        sectionHeading=None,
        snippet="Net 30 days from invoice receipt...",
        chunkId="chunk_987",
        score=0.92,
    )

    assert request.mode.value == "grounded"
    assert pending.status.value == "waiting_for_index"
    assert citation.model_dump(by_alias=True)["chunkId"] == "chunk_987"
