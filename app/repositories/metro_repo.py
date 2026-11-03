"""Repository for MetroStation queries.

Nearby-station searches use the Haversine formula computed in Python rather
than PostGIS spatial queries.  This is acceptable for Bangalore's ~70-station
metro network.  In production with a larger dataset, the ``get_nearby_stations``
query should be replaced with a PostGIS ``ST_DWithin`` / ``ST_Distance``
call for O(log n) performance.
"""

from __future__ import annotations

import logging
import math

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metro import MetroStation

logger = logging.getLogger(__name__)

# ── Haversine helper ──────────────────────────────────────────────────────

_EARTH_RADIUS_M = 6_371_000  # mean Earth radius in metres


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return the great-circle distance in **metres** between two points.

    Uses the standard Haversine formula for spherical geometry.
    """
    rlat1, rlng1, rlat2, rlng2 = (
        math.radians(lat1),
        math.radians(lng1),
        math.radians(lat2),
        math.radians(lng2),
    )
    dlat = rlat2 - rlat1
    dlng = rlng2 - rlng1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return _EARTH_RADIUS_M * c


class MetroRepository:
    """Data-access layer for :class:`MetroStation` entities."""

    # ── Bulk reads ────────────────────────────────────────────────────────

    @staticmethod
    async def get_all_stations(db: AsyncSession) -> list[MetroStation]:
        """Return every metro station, ordered by line then station_order."""
        stmt = select(MetroStation).order_by(
            MetroStation.line, MetroStation.station_order
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ── Single-record reads ───────────────────────────────────────────────

    @staticmethod
    async def get_station_by_code(
        db: AsyncSession,
        code: str,
    ) -> MetroStation | None:
        """Fetch a station by its unique code (e.g. ``'MG'``)."""
        stmt = select(MetroStation).where(MetroStation.code == code)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ── Nearby search (Haversine in Python) ───────────────────────────────

    @staticmethod
    async def get_nearby_stations(
        db: AsyncSession,
        lat: float,
        lng: float,
        radius_m: int = 1500,
        limit: int = 5,
    ) -> list[dict]:
        """Find metro stations within *radius_m* of (lat, lng).

        Returns a list of dicts with keys ``station`` (:class:`MetroStation`)
        and ``distance_m`` (float), sorted by distance ascending.

        .. note::
            This implementation fetches **all** stations and computes
            distances in Python.  This is efficient for Bangalore's ≈70
            stations but would not scale to thousands.  In production,
            replace with a PostGIS ``ST_DWithin`` query::

                SELECT *, ST_Distance(
                    geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
                ) AS distance_m
                FROM metro_stations
                WHERE ST_DWithin(
                    geom,
                    ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                    :radius_m
                )
                ORDER BY distance_m
                LIMIT :limit;
        """
        all_stations = await MetroRepository.get_all_stations(db)

        nearby: list[dict] = []
        for station in all_stations:
            dist = _haversine_m(lat, lng, station.latitude, station.longitude)
            if dist <= radius_m:
                nearby.append({"station": station, "distance_m": round(dist, 1)})

        # Sort by distance and apply limit
        nearby.sort(key=lambda x: x["distance_m"])
        return nearby[:limit]

    # ── Filtered reads ────────────────────────────────────────────────────

    @staticmethod
    async def get_stations_by_line(
        db: AsyncSession,
        line_code: str,
    ) -> list[MetroStation]:
        """Return all stations on a given line, ordered by station_order."""
        stmt = (
            select(MetroStation)
            .where(MetroStation.line == line_code)
            .order_by(MetroStation.station_order)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_interchange_stations(db: AsyncSession) -> list[MetroStation]:
        """Return all interchange stations (where lines cross)."""
        stmt = (
            select(MetroStation)
            .where(MetroStation.is_interchange.is_(True))
            .order_by(MetroStation.name)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
