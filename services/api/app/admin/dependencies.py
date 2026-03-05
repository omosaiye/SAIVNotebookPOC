from __future__ import annotations

from services.api.app.admin.service import AdminService, AdminSettingsStore
from services.api.app.auth.dependencies import get_audit_service
from services.api.app.files.dependencies import get_file_repository, get_ingestion_queue
from services.shared.config import load_api_settings

_SETTINGS_STORE: AdminSettingsStore | None = None


def _get_settings_store() -> AdminSettingsStore:
    global _SETTINGS_STORE
    if _SETTINGS_STORE is None:
        _SETTINGS_STORE = AdminSettingsStore(seed=load_api_settings())
    return _SETTINGS_STORE


def get_admin_service() -> AdminService:
    return AdminService(
        settings_store=_get_settings_store(),
        file_repository=get_file_repository(),
        ingestion_queue=get_ingestion_queue(),
        audit_service=get_audit_service(),
    )


def reset_admin_dependencies() -> None:
    global _SETTINGS_STORE
    _SETTINGS_STORE = None
