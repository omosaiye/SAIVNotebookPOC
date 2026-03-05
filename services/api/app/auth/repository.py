from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4

from services.api.app.auth.models import (
    AuditEventRecord,
    AuthSessionRecord,
    UserRecord,
    WorkspaceMembershipRecord,
)


class InMemoryAuthRepository:
    def __init__(self) -> None:
        self._users_by_id: dict[str, UserRecord] = {}
        self._user_id_by_email: dict[str, str] = {}
        self._memberships: list[WorkspaceMembershipRecord] = []
        self._sessions_by_token: dict[str, AuthSessionRecord] = {}
        self._audit_events: list[AuditEventRecord] = []
        self._lock = Lock()

    def clear(self) -> None:
        with self._lock:
            self._users_by_id.clear()
            self._user_id_by_email.clear()
            self._memberships.clear()
            self._sessions_by_token.clear()
            self._audit_events.clear()

    def put_user(self, user: UserRecord) -> None:
        with self._lock:
            self._users_by_id[user.user_id] = user
            self._user_id_by_email[user.email.lower()] = user.user_id

    def get_user_by_email(self, email: str) -> UserRecord | None:
        user_id = self._user_id_by_email.get(email.lower())
        if user_id is None:
            return None
        return self._users_by_id.get(user_id)

    def get_user_by_id(self, user_id: str) -> UserRecord | None:
        return self._users_by_id.get(user_id)

    def put_membership(self, membership: WorkspaceMembershipRecord) -> None:
        with self._lock:
            self._memberships = [
                item
                for item in self._memberships
                if not (
                    item.user_id == membership.user_id
                    and item.workspace_id == membership.workspace_id
                )
            ]
            self._memberships.append(membership)

    def get_membership(
        self,
        *,
        user_id: str,
        workspace_id: str,
    ) -> WorkspaceMembershipRecord | None:
        return next(
            (
                item
                for item in self._memberships
                if item.user_id == user_id and item.workspace_id == workspace_id
            ),
            None,
        )

    def list_workspace_ids_for_user(self, user_id: str) -> list[str]:
        values = [item.workspace_id for item in self._memberships if item.user_id == user_id]
        return sorted(set(values))

    def put_session(self, session: AuthSessionRecord) -> None:
        with self._lock:
            self._sessions_by_token[session.token] = session

    def get_session(self, token: str) -> AuthSessionRecord | None:
        return self._sessions_by_token.get(token)

    def remove_session(self, token: str) -> None:
        with self._lock:
            self._sessions_by_token.pop(token, None)

    def record_audit_event(
        self,
        *,
        actor_user_id: str | None,
        workspace_id: str | None,
        entity_type: str,
        entity_id: str | None,
        action: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEventRecord:
        event = AuditEventRecord(
            id=f"audit_{uuid4().hex}",
            actorUserId=actor_user_id,
            workspaceId=workspace_id,
            entityType=entity_type,
            entityId=entity_id,
            action=action,
            metadata=metadata or {},
            createdAt=datetime.now(tz=timezone.utc),
        )
        with self._lock:
            self._audit_events.append(event)
        return event

    def list_audit_events(
        self,
        *,
        actor_user_id: str | None = None,
        workspace_id: str | None = None,
    ) -> list[AuditEventRecord]:
        rows = list(self._audit_events)
        if actor_user_id is not None:
            rows = [item for item in rows if item.actor_user_id == actor_user_id]
        if workspace_id is not None:
            rows = [item for item in rows if item.workspace_id == workspace_id]
        return sorted(rows, key=lambda item: item.created_at, reverse=True)

    def purge_expired_sessions(self) -> None:
        now = datetime.now(tz=timezone.utc)
        with self._lock:
            expired = [
                token
                for token, row in self._sessions_by_token.items()
                if row.expires_at <= now
            ]
            for token in expired:
                self._sessions_by_token.pop(token, None)

