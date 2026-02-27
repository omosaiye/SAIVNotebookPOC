from __future__ import annotations

from pathlib import Path


class ObjectStoreClient:
    """Simple object reader for local/dev object-key backed files."""

    def __init__(self, base_path: str | None = None) -> None:
        self._base_path = Path(base_path).resolve() if base_path else None

    def get_bytes(self, object_key: str) -> bytes:
        path = Path(object_key)
        if not path.is_absolute() and self._base_path:
            path = self._base_path / path
        with path.open("rb") as handle:
            return handle.read()
