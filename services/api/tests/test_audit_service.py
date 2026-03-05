from __future__ import annotations

from services.api.app.auth.audit import AuditService
from services.api.app.auth.repository import InMemoryAuthRepository


def test_audit_service_records_rows_with_metadata() -> None:
    repository = InMemoryAuthRepository()
    service = AuditService(repository=repository)

    event = service.record_event(
        action="file_uploaded",
        entity_type="file",
        entity_id="file_123",
        actor_user_id="user_1",
        workspace_id="ws_1",
        metadata={"sizeBytes": 42},
    )

    assert event.action == "file_uploaded"
    assert event.metadata["sizeBytes"] == 42
    assert event.workspace_id == "ws_1"

    events = service.list_events(actor_user_id="user_1", workspace_id="ws_1")
    assert len(events) == 1
    assert events[0].id == event.id

