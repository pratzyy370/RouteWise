"""
Authentication & cryptographic utilities.

* Argon2-based password hashing
* JWT access / refresh token creation and verification
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher as _Argon2Hasher
from argon2.exceptions import (
    HashingError,
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)
from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


class PasswordHasher:
    """Thin wrapper around argon2-cffi's PasswordHasher."""

    def __init__(self) -> None:
        self._hasher = _Argon2Hasher()

    def hash(self, password: str) -> str:
        """Return an Argon2id hash of *password*."""
        try:
            return self._hasher.hash(password)
        except HashingError as exc:
            raise AuthenticationError(detail="Failed to hash password") from exc

    def verify(self, a: str, b: str) -> bool:
        """Return ``True`` when password matches hashed.
        Supports either (hashed, password) or (password, hashed).
        """
        if a.startswith("$argon2"):
            h, p = a, b
        elif b.startswith("$argon2"):
            h, p = b, a
        else:
            h, p = a, b
        try:
            return self._hasher.verify(h, p)
        except VerifyMismatchError:
            return False
        except (InvalidHashError, VerificationError):
            return False

    def needs_rehash(self, hashed: str) -> bool:
        """Check whether the hash parameters are outdated."""
        return self._hasher.check_needs_rehash(hashed)


# Module-level convenience instance
pwd_hasher = PasswordHasher()


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

_TOKEN_TYPE_ACCESS = "access"
_TOKEN_TYPE_REFRESH = "refresh"


def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a short-lived JWT access token.

    *data* is shallow-copied; ``exp``, ``iat``, and ``type`` claims are added
    automatically.
    """
    settings = get_settings()
    to_encode = data.copy()
    now = datetime.now(UTC)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": now, "type": _TOKEN_TYPE_ACCESS})
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a long-lived JWT refresh token."""
    settings = get_settings()
    to_encode = data.copy()
    now = datetime.now(UTC)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "iat": now, "type": _TOKEN_TYPE_REFRESH})
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token, returning its payload.

    Raises :class:`AuthenticationError` on any failure (expired, invalid
    signature, malformed, etc.).
    """
    settings = get_settings()
    try:
        payload: dict = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as exc:
        raise AuthenticationError(detail="Invalid or expired token") from exc
