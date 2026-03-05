from __future__ import annotations

import hashlib
import math

DEFAULT_EMBEDDING_DIMS = 32


def deterministic_embedding(text: str, *, dimensions: int = DEFAULT_EMBEDDING_DIMS) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    repeated = (digest * ((dimensions // len(digest)) + 1))[:dimensions]
    raw = [((byte / 255.0) * 2.0) - 1.0 for byte in repeated]
    norm = math.sqrt(sum(value * value for value in raw)) or 1.0
    return [value / norm for value in raw]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    length = min(len(a), len(b))
    dot = sum(a[idx] * b[idx] for idx in range(length))
    norm_a = math.sqrt(sum(value * value for value in a[:length])) or 1.0
    norm_b = math.sqrt(sum(value * value for value in b[:length])) or 1.0
    return dot / (norm_a * norm_b)

