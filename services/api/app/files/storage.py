from __future__ import annotations

from pathlib import Path


class ObjectStorage:
    def put(self, object_key: str, payload: bytes) -> None:
        raise NotImplementedError

    def delete(self, object_key: str) -> None:
        raise NotImplementedError


class LocalObjectStorage(ObjectStorage):
    def __init__(self, base_path: Path) -> None:
        self._base_path = base_path

    def put(self, object_key: str, payload: bytes) -> None:
        target = self._base_path / object_key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)

    def delete(self, object_key: str) -> None:
        target = self._base_path / object_key
        if target.exists():
            target.unlink()
