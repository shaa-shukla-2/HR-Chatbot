"""Password hashing and signed login tokens (JWT) for the HR assistant.

Passwords are never stored in plain text. Tokens carry only the employee ID and
role; the backend always reads *who is asking* from the token, never from the
text of the chat message.
"""

import hashlib
import hmac
import os
import time

import jwt

ALGORITHM = "HS256"
_SCHEME = "pbkdf2_sha256"
_ITERATIONS = 200_000


def hash_password(password: str, *, iterations: int = _ITERATIONS) -> str:
    """Return a salted PBKDF2 hash string: scheme$iterations$salt_hex$hash_hex."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{_SCHEME}${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Check a password against a stored hash in constant time."""
    try:
        scheme, iterations, salt_hex, hash_hex = stored_hash.split("$")
        if scheme != _SCHEME:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest, bytes.fromhex(hash_hex))
    except (ValueError, TypeError, AttributeError):
        return False


def create_access_token(
    employee_id: str,
    role: str,
    secret: str,
    *,
    minutes: int = 60,
    now: float | None = None,
) -> str:
    """Create a signed token that expires after `minutes`."""
    issued = int(time.time() if now is None else now)
    payload = {
        "sub": employee_id,
        "role": role,
        "iat": issued,
        "exp": issued + minutes * 60,
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_access_token(token: str, secret: str) -> dict:
    """Return the token claims, or raise jwt.InvalidTokenError (including expiry)."""
    return jwt.decode(token, secret, algorithms=[ALGORITHM])
