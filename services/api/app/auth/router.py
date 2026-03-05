from __future__ import annotations

from fastapi import APIRouter, Depends

from services.api.app.auth.dependencies import (
    get_auth_service,
    get_current_user,
    list_audit_events_for_user,
)
from services.api.app.auth.models import (
    AuditEventRecord,
    AuthContext,
    AuthProfileResponse,
    LoginRequest,
    LoginResponse,
)
from services.api.app.auth.service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    return auth_service.login(email=payload.email, password=payload.password)


@router.get("/me", response_model=AuthProfileResponse)
def me(
    auth_context: AuthContext = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthProfileResponse:
    return auth_service.get_profile(auth_context=auth_context)


@router.get("/audit-events", response_model=list[AuditEventRecord])
def list_my_audit_events(
    events: list[AuditEventRecord] = Depends(list_audit_events_for_user),
) -> list[AuditEventRecord]:
    return events

