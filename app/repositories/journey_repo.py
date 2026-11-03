"""Repository for JourneySearch, JourneyOption, and JourneyLeg persistence."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.journey import JourneyLeg, JourneyOption, JourneySearch

logger = logging.getLogger(__name__)


class JourneyRepository:
    """Data-access layer for journey search, option, and leg entities."""

    # ── JourneySearch ─────────────────────────────────────────────────────

    @staticmethod
    async def create_search(
        db: AsyncSession,
        search_data: dict[str, Any],
    ) -> JourneySearch:
        """Persist a new journey search record.

        ``search_data`` should contain ``origin_lat``, ``origin_lng``,
        ``dest_lat``, ``dest_lng``, ``preference``, and optionally
        ``user_id``, ``origin_address``, ``dest_address``.
        """
        search = JourneySearch(
            user_id=search_data.get("user_id"),
            origin_lat=search_data["origin_lat"],
            origin_lng=search_data["origin_lng"],
            dest_lat=search_data["dest_lat"],
            dest_lng=search_data["dest_lng"],
            origin_address=search_data.get("origin_address"),
            dest_address=search_data.get("dest_address"),
            preference=search_data.get("preference", "balanced"),
        )
        db.add(search)
        await db.flush()
        await db.refresh(search)
        logger.info(
            "Created journey search id=%s (%s,%s) → (%s,%s)",
            search.id,
            search.origin_lat,
            search.origin_lng,
            search.dest_lat,
            search.dest_lng,
        )
        return search

    # ── JourneyOption ─────────────────────────────────────────────────────

    @staticmethod
    async def create_option(
        db: AsyncSession,
        option_data: dict[str, Any],
    ) -> JourneyOption:
        """Persist a single journey option linked to a search.

        ``option_data`` must include ``search_id``, ``rank``, ``total_cost``,
        ``total_duration_minutes``, ``score``, and optionally
        ``is_recommended``, ``total_distance_m``, ``walking_distance_m``,
        ``transfer_count``, ``recommendation_reason``.
        """
        option = JourneyOption(
            search_id=option_data["search_id"],
            rank=option_data["rank"],
            is_recommended=option_data.get("is_recommended", False),
            total_cost=option_data["total_cost"],
            total_duration_minutes=option_data["total_duration_minutes"],
            total_distance_m=option_data.get("total_distance_m"),
            walking_distance_m=option_data.get("walking_distance_m", 0.0),
            transfer_count=option_data.get("transfer_count", 0),
            score=option_data["score"],
            recommendation_reason=option_data.get("recommendation_reason"),
        )
        db.add(option)
        await db.flush()
        await db.refresh(option)
        logger.info(
            "Created journey option id=%s rank=%s for search=%s",
            option.id,
            option.rank,
            option.search_id,
        )
        return option

    # ── JourneyLeg ────────────────────────────────────────────────────────

    @staticmethod
    async def create_leg(
        db: AsyncSession,
        leg_data: dict[str, Any],
    ) -> JourneyLeg:
        """Persist a single journey leg linked to an option.

        ``leg_data`` must include ``option_id``, ``leg_order``, ``mode``,
        coordinate fields, ``estimated_cost``, ``estimated_duration_minutes``,
        ``data_source``, and optionally ``distance_m``, ``provider``,
        ``confidence``, ``origin_name``, ``dest_name``.
        """
        leg = JourneyLeg(
            option_id=leg_data["option_id"],
            leg_order=leg_data["leg_order"],
            mode=leg_data["mode"],
            origin_lat=leg_data["origin_lat"],
            origin_lng=leg_data["origin_lng"],
            dest_lat=leg_data["dest_lat"],
            dest_lng=leg_data["dest_lng"],
            origin_name=leg_data.get("origin_name"),
            dest_name=leg_data.get("dest_name"),
            estimated_cost=leg_data["estimated_cost"],
            estimated_duration_minutes=leg_data["estimated_duration_minutes"],
            distance_m=leg_data.get("distance_m"),
            provider=leg_data.get("provider"),
            data_source=leg_data.get("data_source", "demo"),
            confidence=leg_data.get("confidence"),
        )
        db.add(leg)
        await db.flush()
        await db.refresh(leg)
        logger.info(
            "Created journey leg id=%s order=%s mode=%s for option=%s",
            leg.id,
            leg.leg_order,
            leg.mode,
            leg.option_id,
        )
        return leg

    # ── Composite read ────────────────────────────────────────────────────

    @staticmethod
    async def get_search_with_options(
        db: AsyncSession,
        search_id: uuid.UUID,
    ) -> JourneySearch | None:
        """Load a search together with its options and each option's legs.

        Uses ``selectinload`` to eagerly fetch the full tree in a minimal
        number of queries.  Returns ``None`` when the search does not exist.
        """
        stmt = (
            select(JourneySearch)
            .where(JourneySearch.id == search_id)
            .options(
                selectinload(JourneySearch.options).selectinload(
                    JourneyOption.legs
                )
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
