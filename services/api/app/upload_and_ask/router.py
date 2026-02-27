from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from services.api.app.files.dependencies import get_workspace_id
from services.api.app.upload_and_ask.dependencies import get_upload_and_ask_service
from services.api.app.upload_and_ask.models import UploadAndAskCreateResult, UploadAndAskStatusResponse
from services.api.app.upload_and_ask.service import UploadAndAskService
from services.shared.enums import UploadAndAskScope

router = APIRouter(prefix="/api/v1/upload-and-ask", tags=["upload-and-ask"])


@router.post("", response_model=UploadAndAskCreateResult)
async def create_upload_and_ask_request(
    query: Annotated[str, Form()],
    files: Annotated[list[UploadFile], File()],
    scope: Annotated[UploadAndAskScope, Form()] = UploadAndAskScope.UPLOADED_FILES_ONLY,
    workspace_id: str = Depends(get_workspace_id),
    service: UploadAndAskService = Depends(get_upload_and_ask_service),
) -> UploadAndAskCreateResult:
    return await service.create_request(
        workspace_id=workspace_id,
        query=query,
        files=files,
        scope=scope,
    )


@router.get("/{request_id}", response_model=UploadAndAskStatusResponse)
def get_upload_and_ask_request(
    request_id: str,
    workspace_id: str = Depends(get_workspace_id),
    service: UploadAndAskService = Depends(get_upload_and_ask_service),
) -> UploadAndAskStatusResponse:
    return service.get_request(workspace_id=workspace_id, request_id=request_id)
