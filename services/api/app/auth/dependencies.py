from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from services.api.app.auth.audit import AuditService
from services.api.app.auth.models import (
    AuditEventRecord,
    AuthContext,
    WorkspaceAccessContext,
)
from services.api.app.auth.repository import InMemoryAuthRepository
from services.api.app.auth.service import AuthService
from services.shared.config import load_api_settings

_AUTH_REPOSITORY = InMemoryAuthRepository()
_AUDIT_SERVICE = AuditService(repository=_AUTH_REPOSITORY)
_AUTH_SERVICE: AuthService | None = None


def _build_auth_service() -> AuthService:
    settings = load_api_settings()
    service = AuthService(
        repository=_AUTH_REPOSITORY,
        audit_service=_AUDIT_SERVICE,
        session_ttl_minutes=settings.auth_session_ttl_minutes,
    )
    if settings.auth_seed_enabled:
        workspace_ids = [
            value.strip()
            for value in settings.auth_seed_workspace_ids.split(",")
            if value.strip()
        ]
        if not workspace_ids:
            workspace_ids = ["ws_1"]
        service.ensure_seed_user(
            user_id=settings.auth_seed_user_id,
            email=settings.auth_seed_email,
            password=settings.auth_seed_password,
            workspace_ids=workspace_ids,
        )
    return service


def get_auth_service() -> AuthService:
    global _AUTH_SERVICE
    if _AUTH_SERVICE is None:
        _AUTH_SERVICE = _build_auth_service()
    return _AUTH_SERVICE


def get_audit_service() -> AuditService:
    return _AUDIT_SERVICE


def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthContext:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization scheme",
        )
    return auth_service.authenticate_token(token)


def get_workspace_access(
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    auth_context: AuthContext = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> WorkspaceAccessContext:
    if not x_workspace_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing workspace authorization",
        )
    return auth_service.authorize_workspace(
        auth_context=auth_context,
        workspace_id=x_workspace_id,
    )


def list_audit_events_for_user(
    auth_context: AuthContext = Depends(get_current_user),
    audit_service: AuditService = Depends(get_audit_service),
) -> list[AuditEventRecord]:
    return audit_service.list_events(actor_user_id=auth_context.user_id)


def reset_auth_dependencies() -> None:
    global _AUTH_SERVICE
    _AUTH_SERVICE = None
    _AUTH_REPOSITORY.clear()
