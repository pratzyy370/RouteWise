"""Repository for SavedPlace CRUD operations with ownership enforcement."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.place import SavedPlace

logger = logging.getLogger(__name__)


class PlaceRepository:
    """Data-access layer for :class:`SavedPlace` entities.

    Every query is scoped to the owning ``user_id`` to enforce row-level
    ownership without relying on database-level RLS.
    """

    # ── Read ──────────────────────────────────────────────────────────────

    @staticmethod
    async def get_user_places(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[SavedPlace]:
        """Return all saved places belonging to *user_id*, ordered by name."""
        stmt = (
            select(SavedPlace)
            .where(SavedPlace.user_id == user_id)
            .order_by(SavedPlace.name)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        place_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
    ) -> SavedPlace | None:
        """Fetch a single place by primary key.

        When *user_id* is supplied the query also enforces ownership.
        Returns ``None`` if not found (or not owned).
        """
        conditions = [SavedPlace.id == place_id]
        if user_id is not None:
            conditions.append(SavedPlace.user_id == user_id)
        stmt = select(SavedPlace).where(and_(*conditions))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ── Create ────────────────────────────────────────────────────────────

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: uuid.UUID,
        data: dict[str, Any],
    ) -> SavedPlace:
        """Create a new saved place for *user_id*.

        Returns the flushed :class:`SavedPlace` with ``id`` populated.
        """
        place = SavedPlace(
            user_id=user_id,
            name=data["name"],
            label=data.get("label", "other"),
            latitude=data["latitude"],
            longitude=data["longitude"],
            address=data.get("address"),
        )
        db.add(place)
        await db.flush()
        await db.refresh(place)
        logger.info(
            "Created saved place id=%s name=%r for user=%s",
            place.id,
            place.name,
            user_id,
        )
        return place

    # ── Update ────────────────────────────────────────────────────────────

    @staticmethod
    async def update(
        db: AsyncSession,
        place_id: uuid.UUID,
        data: dict[str, Any],
        *,
        user_id: uuid.UUID | None = None,
    ) -> SavedPlace | None:
        """Partially update a saved place.

        When *user_id* is given, ownership is enforced.  Returns the
        updated place, or ``None`` if not found / not owned.
        """
        conditions = [SavedPlace.id == place_id]
        if user_id is not None:
            conditions.append(SavedPlace.user_id == user_id)
        stmt = select(SavedPlace).where(and_(*conditions))
        result = await db.execute(stmt)
        place = result.scalar_one_or_none()
        if place is None:
            return None

        allowed_fields = {"name", "label", "latitude", "longitude", "address"}
        for key, value in data.items():
            if key in allowed_fields and value is not None:
                setattr(place, key, value)

        await db.flush()
        await db.refresh(place)
        logger.info("Updated saved place id=%s fields=%s", place_id, list(data.keys()))
        return place

    # ── Delete ────────────────────────────────────────────────────────────

    @staticmethod
    async def delete(
        db: AsyncSession,
        place_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
    ) -> bool:
        """Delete a saved place by id.

        When *user_id* is given, ownership is enforced.  Returns ``True``
        if a row was deleted, ``False`` otherwise.
        """
        conditions = [SavedPlace.id == place_id]
        if user_id is not None:
            conditions.append(SavedPlace.user_id == user_id)
        stmt = select(SavedPlace).where(and_(*conditions))
        result = await db.execute(stmt)
        place = result.scalar_one_or_none()
        if place is None:
            return False

        await db.delete(place)
        await db.flush()
        logger.info("Deleted saved place id=%s", place_id)
        return True
