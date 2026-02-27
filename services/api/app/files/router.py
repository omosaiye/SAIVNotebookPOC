from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query, Request

from services.api.app.files.dependencies import get_file_service, get_workspace_id
from services.api.app.files.service import FileService
from services.shared.contracts import FileDetail, FileSummary, UploadResponse
from services.shared.enums import FileStatus

router = APIRouter(prefix="/api/v1/files", tags=["files"])


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    request: Request,
    x_file_name: str = Header(alias="X-File-Name"),
    content_type: str | None = Header(default=None, alias="Content-Type"),
    workspace_id: str = Depends(get_workspace_id),
    service: FileService = Depends(get_file_service),
) -> UploadResponse:
    return await service.upload(
        workspace_id=workspace_id,
        filename=x_file_name,
        payload=await request.body(),
        declared_mime=content_type,
    )


@router.get("", response_model=list[FileSummary])
def list_files(
    status: FileStatus | None = Query(default=None),
    search: str | None = Query(default=None),
    include_deleted: bool = Query(default=False, alias="includeDeleted"),
    workspace_id: str = Depends(get_workspace_id),
    service: FileService = Depends(get_file_service),
) -> list[FileSummary]:
    return service.list_files(
        workspace_id=workspace_id,
        status=status,
        search=search,
        include_deleted=include_deleted,
    )


@router.get("/{file_id}", response_model=FileDetail)
def get_file(
    file_id: str,
    workspace_id: str = Depends(get_workspace_id),
    service: FileService = Depends(get_file_service),
) -> FileDetail:
    return service.get_file(workspace_id=workspace_id, file_id=file_id)


@router.get("/{file_id}/status", response_model=UploadResponse)
def get_file_status(
    file_id: str,
    workspace_id: str = Depends(get_workspace_id),
    service: FileService = Depends(get_file_service),
) -> UploadResponse:
    detail = service.get_file(workspace_id=workspace_id, file_id=file_id)
    return UploadResponse(
        fileId=detail.id,
        status=detail.status,
        message="Current ingestion status",
    )


@router.post("/{file_id}/reprocess", response_model=UploadResponse)
def reprocess_file(
    file_id: str,
    workspace_id: str = Depends(get_workspace_id),
    service: FileService = Depends(get_file_service),
) -> UploadResponse:
    return service.reprocess(workspace_id=workspace_id, file_id=file_id)


@router.delete("/{file_id}", response_model=UploadResponse)
def delete_file(
    file_id: str,
    workspace_id: str = Depends(get_workspace_id),
    service: FileService = Depends(get_file_service),
) -> UploadResponse:
    return service.delete(workspace_id=workspace_id, file_id=file_id)
