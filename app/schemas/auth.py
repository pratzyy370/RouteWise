"""Authentication and user-related Pydantic v2 schemas."""

from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    """Payload for new user registration."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ..., min_length=8, description="Password (min 8 characters)"
    )
    full_name: str = Field(
        ..., min_length=1, max_length=120, description="Full display name"
    )

    @field_validator("email")
    @classmethod
    def validate_email_pattern(cls, v: str) -> str:
        """Reject disposable / overly exotic addresses."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, v):
            raise ValueError("Invalid email format")
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        return v


class UserLogin(BaseModel):
    """Credentials for login."""

    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        return v.lower()


class TokenResponse(BaseModel):
    """JWT token pair returned after successful authentication."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Public representation of a user (never includes password)."""

    id: UUID
    email: str
    full_name: str
    is_active: bool
    is_verified: bool
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """Partial-update payload for the current user profile."""

    full_name: str | None = Field(None, min_length=1, max_length=120)
    email: EmailStr | None = None

    @field_validator("email")
    @classmethod
    def normalise_email(cls, v: str | None) -> str | None:
        return v.lower() if v else v
