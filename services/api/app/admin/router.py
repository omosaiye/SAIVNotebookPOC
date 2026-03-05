from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from services.api.app.admin.dependencies import get_admin_service
from services.api.app.admin.models import (
    AdminMetricsResponse,
    AdminSettingsPatchRequest,
    AdminSettingsResponse,
    IngestionJobRow,
    IngestionLogRow,
)
from services.api.app.admin.service import AdminService
from services.api.app.auth.dependencies import get_workspace_access
from services.api.app.auth.models import WorkspaceAccessContext

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _assert_admin_role(workspace_access: WorkspaceAccessContext) -> None:
    if workspace_access.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Admin role required")


@router.get("/settings", response_model=AdminSettingsResponse)
def get_settings(
    workspace_access: WorkspaceAccessContext = Depends(get_workspace_access),
    service: AdminService = Depends(get_admin_service),
) -> AdminSettingsResponse:
    _assert_admin_role(workspace_access)
    return service.get_settings()


@router.patch("/settings", response_model=AdminSettingsResponse)
def update_settings(
    payload: AdminSettingsPatchRequest,
    workspace_access: WorkspaceAccessContext = Depends(get_workspace_access),
    service: AdminService = Depends(get_admin_service),
) -> AdminSettingsResponse:
    _assert_admin_role(workspace_access)
    return service.update_settings(payload)


@router.get("/ingestion-jobs", response_model=list[IngestionJobRow])
def list_ingestion_jobs(
    include_deleted: bool = Query(default=False, alias="includeDeleted"),
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    workspace_access: WorkspaceAccessContext = Depends(get_workspace_access),
    service: AdminService = Depends(get_admin_service),
) -> list[IngestionJobRow]:
    _assert_admin_role(workspace_access)
    return service.list_ingestion_jobs(
        workspace_id=workspace_access.workspace_id,
        include_deleted=include_deleted,
        limit=limit,
    )


@router.get("/ingestion-logs", response_model=list[IngestionLogRow])
def list_ingestion_logs(
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    workspace_access: WorkspaceAccessContext = Depends(get_workspace_access),
    service: AdminService = Depends(get_admin_service),
) -> list[IngestionLogRow]:
    _assert_admin_role(workspace_access)
    return service.list_ingestion_logs(
        workspace_id=workspace_access.workspace_id,
        limit=limit,
    )


@router.get("/metrics", response_model=AdminMetricsResponse)
def get_metrics(
    workspace_access: WorkspaceAccessContext = Depends(get_workspace_access),
    service: AdminService = Depends(get_admin_service),
) -> AdminMetricsResponse:
    _assert_admin_role(workspace_access)
    return service.get_metrics(workspace_id=workspace_access.workspace_id)
