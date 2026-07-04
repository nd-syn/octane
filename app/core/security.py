"""Password hashing and JWT utilities.

- Passwords: Argon2id via argon2-cffi. The default parameters are tuned
  for ~50ms hashing on a modern CPU and use ~19 MiB of memory, which fits
  comfortably in Render's free-tier 512 MiB container even with concurrent
  logins.
- JWTs: HS256. Access token short-lived (15 min). Refresh token long-lived
  (30 days) and stored hashed in the DB so logout can revoke.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError, VerificationError

from app.core.crypto import random_token
from app.core.exceptions import TokenExpired, TokenInvalid


# Argon2id with library defaults. memory_cost ~ 19 MiB, time_cost ~ 2.
_hasher = PasswordHasher()


# ---------- passwords ----------

def hash_password(plaintext: str) -> str:
    """Hash a password. Returns the encoded string for DB storage."""
    return _hasher.hash(plaintext)


def verify_password(plaintext: str, encoded_hash: str) -> bool:
    """Verify a password against the stored hash."""
    try:
        return _hasher.verify(encoded_hash, plaintext)
    except (VerifyMismatchError, InvalidHashError, VerificationError):
        return False


# ---------- JWT ----------

ACCESS_TYPE = "access"
REFRESH_TYPE = "refresh"


def _now() -> int:
    return int(time.time())


def encode_access_token(
    *, user_id: int, secret: bytes, ttl_seconds: int
) -> str:
    """Build a short-lived access token."""
    now = _now()
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + ttl_seconds,
        "jti": uuid.uuid4().hex,
        "typ": ACCESS_TYPE,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def encode_refresh_token(
    *, user_id: int, secret: bytes, ttl_seconds: int
) -> tuple[str, str]:
    """Build a refresh token. Returns (jwt, plain_token_str).

    The plain_token_str is what the client stores; the server stores
    SHA-256(jwt) in the DB so it can verify and revoke.
    """
    now = _now()
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + ttl_seconds,
        "jti": uuid.uuid4().hex,
        "typ": REFRESH_TYPE,
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token, token  # identity for now; client gets the same string


def hash_refresh_token(token: str) -> str:
    """SHA-256 of the refresh token, hex. Stored in the DB."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def decode_token(token: str, secret: bytes) -> dict[str, Any]:
    """Decode and validate a JWT. Raises TokenExpired / TokenInvalid."""
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as e:
        raise TokenExpired("token expired") from e
    except jwt.InvalidTokenError as e:
        raise TokenInvalid("invalid token") from e


def generate_session_token() -> str:
    """Random URL-safe token (e.g. for future session IDs, not used in v1)."""
    return random_token()
