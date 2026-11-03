"""Repository for User CRUD operations."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import pwd_hasher
from app.models.user import User

logger = logging.getLogger(__name__)


class UserRepository:
    """Data-access layer for :class:`User` entities."""

    # ── Read ──────────────────────────────────────────────────────────────

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
        """Fetch a user by primary key.

        Returns ``None`` when the user does not exist.
        """
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> User | None:
        """Fetch a user by email (case-insensitive lookup).

        Returns ``None`` when no matching user is found.
        """
        stmt = select(User).where(User.email == email.lower())
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ── Create ────────────────────────────────────────────────────────────

    @staticmethod
    async def create(db: AsyncSession, user_data: dict[str, Any]) -> User:
        """Insert a new user record.

        ``user_data`` must contain at minimum ``email``, ``password``, and
        ``full_name``.  The plaintext password is hashed before storage.

        Returns the newly-created :class:`User` instance (already flushed
        so ``id`` and ``created_at`` are populated).
        """
        hashed_password = pwd_hasher.hash(user_data.pop("password"))

        user = User(
            email=user_data["email"].lower(),
            hashed_password=hashed_password,
            full_name=user_data["full_name"],
            is_active=user_data.get("is_active", True),
            is_verified=user_data.get("is_verified", False),
            role=user_data.get("role", "user"),
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        logger.info("Created user id=%s email=%s", user.id, user.email)
        return user

    # ── Update ────────────────────────────────────────────────────────────

    @staticmethod
    async def update(
        db: AsyncSession,
        user_id: uuid.UUID,
        data: dict[str, Any],
    ) -> User | None:
        """Partially update an existing user.

        Only keys present in *data* are applied.  Returns the updated
        :class:`User`, or ``None`` if the user was not found.
        """
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            return None

        # Allowlisted mutable fields
        allowed_fields = {"full_name", "email", "is_active", "is_verified", "role"}
        for key, value in data.items():
            if key in allowed_fields and value is not None:
                if key == "email":
                    value = value.lower()
                setattr(user, key, value)

        await db.flush()
        await db.refresh(user)
        logger.info("Updated user id=%s fields=%s", user_id, list(data.keys()))
        return user
