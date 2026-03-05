from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status

from services.api.app.auth.audit import AuditService
from services.api.app.auth.models import (
    AuthContext,
    AuthProfileResponse,
    AuthSessionRecord,
    LoginResponse,
    UserRecord,
    WorkspaceAccessContext,
    WorkspaceMembershipRecord,
)
from services.api.app.auth.repository import InMemoryAuthRepository
from services.api.app.auth.security import create_session_token, hash_password, verify_password


class AuthService:
    def __init__(
        self,
        *,
        repository: InMemoryAuthRepository,
        audit_service: AuditService,
        session_ttl_minutes: int,
    ) -> None:
        self._repository = repository
        self._audit_service = audit_service
        self._session_ttl_minutes = session_ttl_minutes

    def ensure_seed_user(
        self,
        *,
        user_id: str,
        email: str,
        password: str,
        workspace_ids: list[str],
    ) -> None:
        existing = self._repository.get_user_by_email(email)
        effective_user_id = user_id
        if existing is None:
            self._repository.put_user(
                UserRecord(
                    userId=user_id,
                    email=email.lower(),
                    passwordHash=hash_password(password),
                    isActive=True,
                )
            )
        else:
            effective_user_id = existing.user_id
        for workspace_id in workspace_ids:
            self._repository.put_membership(
                WorkspaceMembershipRecord(
                    workspaceId=workspace_id,
                    userId=effective_user_id,
                    role="owner",
                )
            )

    def login(self, *, email: str, password: str) -> LoginResponse:
        candidate = self._repository.get_user_by_email(email)
        if candidate is None or not candidate.is_active:
            self._audit_service.record_event(
                action="auth_login_failed",
                entity_type="auth",
                metadata={"email": email.lower(), "reason": "unknown_or_inactive_user"},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not verify_password(password, candidate.password_hash):
            self._audit_service.record_event(
                action="auth_login_failed",
                entity_type="auth",
                actor_user_id=candidate.user_id,
                metadata={"reason": "bad_password"},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        now = datetime.now(tz=timezone.utc)
        expires = now + timedelta(minutes=self._session_ttl_minutes)
        token = create_session_token()
        self._repository.put_session(
            AuthSessionRecord(
                token=token,
                userId=candidate.user_id,
                createdAt=now,
                expiresAt=expires,
            )
        )
        workspace_ids = self._repository.list_workspace_ids_for_user(candidate.user_id)

        self._audit_service.record_event(
            action="auth_login_succeeded",
            entity_type="auth",
            actor_user_id=candidate.user_id,
            metadata={"workspaceCount": len(workspace_ids)},
        )
        return LoginResponse(
            accessToken=token,
            tokenType="bearer",
            expiresAt=expires,
            userId=candidate.user_id,
            email=candidate.email,
            workspaceIds=workspace_ids,
        )

    def authenticate_token(self, token: str) -> AuthContext:
        self._repository.purge_expired_sessions()
        session = self._repository.get_session(token)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session token",
            )

        user = self._repository.get_user_by_id(session.user_id)
        if user is None or not user.is_active:
            self._repository.remove_session(token)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session token",
            )
        return AuthContext(userId=user.user_id, email=user.email)

    def authorize_workspace(
        self,
        *,
        auth_context: AuthContext,
        workspace_id: str,
    ) -> WorkspaceAccessContext:
        membership = self._repository.get_membership(
            user_id=auth_context.user_id,
            workspace_id=workspace_id,
        )
        if membership is None:
            self._audit_service.record_event(
                action="workspace_access_denied",
                entity_type="workspace",
                entity_id=workspace_id,
                actor_user_id=auth_context.user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Workspace access denied",
            )
        return WorkspaceAccessContext(
            workspaceId=workspace_id,
            userId=auth_context.user_id,
            role=membership.role,
        )

    def get_profile(self, *, auth_context: AuthContext) -> AuthProfileResponse:
        return AuthProfileResponse(
            userId=auth_context.user_id,
            email=auth_context.email,
            workspaceIds=self._repository.list_workspace_ids_for_user(auth_context.user_id),
        )

    def record_audit(
        self,
        *,
        action: str,
        entity_type: str,
        actor_user_id: str | None = None,
        workspace_id: str | None = None,
        entity_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._audit_service.record_event(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_user_id=actor_user_id,
            workspace_id=workspace_id,
            metadata=metadata,
        )
