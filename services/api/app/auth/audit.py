from __future__ import annotations

from typing import Any

from services.api.app.auth.models import AuditEventRecord
from services.api.app.auth.repository import InMemoryAuthRepository


class AuditService:
    def __init__(self, *, repository: InMemoryAuthRepository) -> None:
        self._repository = repository

    def record_event(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        actor_user_id: str | None = None,
        workspace_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEventRecord:
        return self._repository.record_audit_event(
            actor_user_id=actor_user_id,
            workspace_id=workspace_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            metadata=metadata,
        )

    def list_events(
        self,
        *,
        actor_user_id: str | None = None,
        workspace_id: str | None = None,
    ) -> list[AuditEventRecord]:
        return self._repository.list_audit_events(
            actor_user_id=actor_user_id,
            workspace_id=workspace_id,
        )

