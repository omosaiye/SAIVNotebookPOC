from __future__ import annotations

import hashlib
import hmac
import secrets

PBKDF2_ITERATIONS = 600_000
ALGORITHM = "sha256"


def hash_password(password: str, *, salt: str | None = None) -> str:
    chosen_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        ALGORITHM,
        password.encode("utf-8"),
        chosen_salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_{ALGORITHM}${PBKDF2_ITERATIONS}${chosen_salt}${digest.hex()}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        method, iterations_raw, salt, digest = encoded_hash.split("$", maxsplit=3)
        if method != f"pbkdf2_{ALGORITHM}":
            return False
        iterations = int(iterations_raw)
    except ValueError:
        return False

    derived = hashlib.pbkdf2_hmac(
        ALGORITHM,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return hmac.compare_digest(derived, digest)


def create_session_token() -> str:
    return secrets.token_urlsafe(32)

