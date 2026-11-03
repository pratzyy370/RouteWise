"""
Unit tests for password hashing and JWT token management.
"""

from datetime import timedelta

import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    pwd_hasher,
)


def test_password_hashing():
    password = "SecretPassword123!"
    hashed = pwd_hasher.hash(password)
    assert hashed != password
    assert pwd_hasher.verify(password, hashed) is True
    assert pwd_hasher.verify("WrongPassword!", hashed) is False


def test_jwt_access_token_creation_and_decoding():
    data = {"sub": "12345", "role": "user"}
    token = create_access_token(data=data, expires_delta=timedelta(minutes=15))
    decoded = decode_token(token)

    assert decoded["sub"] == "12345"
    assert decoded["role"] == "user"
    assert decoded["type"] == "access"
    assert "exp" in decoded


def test_jwt_refresh_token():
    data = {"sub": "user-uuid-99"}
    token = create_refresh_token(data=data, expires_delta=timedelta(days=7))
    decoded = decode_token(token)

    assert decoded["sub"] == "user-uuid-99"
    assert decoded["type"] == "refresh"


def test_jwt_expired_token():
    data = {"sub": "expired-user"}
    token = create_access_token(data=data, expires_delta=timedelta(seconds=-10))
    with pytest.raises(Exception):
        decode_token(token)
