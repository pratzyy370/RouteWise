"""
Metro discovery and route planning service for Namma Metro (Bengaluru).
"""

import logging
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metro import MetroStation
from app.repositories.metro_repo import MetroRepository

logger = logging.getLogger(__name__)


def calculate_bmrcl_fare(station_count: int) -> Decimal:
    """
    Standard BMRCL fare structure (approximate official slab):
    1-2 stations: ₹10
    3-5 stations: ₹20
    6-10 stations: ₹30
    11-15 stations: ₹40
    16-20 stations: ₹50
    21+ stations: ₹60 (maximum cap)
    """
    if station_count <= 2:
        return Decimal("10.00")
    elif station_count <= 5:
        return Decimal("20.00")
    elif station_count <= 10:
        return Decimal("30.00")
    elif station_count <= 15:
        return Decimal("40.00")
    elif station_count <= 20:
        return Decimal("50.00")
    else:
        return Decimal("60.00")


class MetroService:
    @staticmethod
    async def get_nearby_stations(
        db: AsyncSession,
        lat: float,
        lng: float,
        radius_m: int = 1500,
        limit: int = 5,
    ) -> list[dict]:
        """Find stations within radius_m using geographic distance."""
        return await MetroRepository.get_nearby_stations(db, lat, lng, radius_m, limit)

    @staticmethod
    async def get_station_by_code(db: AsyncSession, code: str) -> MetroStation | None:
        return await MetroRepository.get_station_by_code(db, code)

    @staticmethod
    async def find_metro_route(
        db: AsyncSession,
        origin_code: str,
        dest_code: str,
    ) -> dict | None:
        """Find metro path between two station codes."""
        orig = await MetroRepository.get_station_by_code(db, origin_code)
        dest = await MetroRepository.get_station_by_code(db, dest_code)
        if not orig or not dest:
            return None

        if orig.code == dest.code:
            return {
                "origin_station": orig,
                "dest_station": dest,
                "station_count": 0,
                "duration_minutes": 0,
                "cost": Decimal("0.00"),
                "has_interchange": False,
                "lines": [orig.line],
            }

        if orig.line == dest.line:
            station_diff = abs(orig.station_order - dest.station_order)
            duration_mins = round(station_diff * 2.2 + 2.0, 1)  # ~2.2 mins per station + wait
            fare = calculate_bmrcl_fare(station_diff)
            return {
                "origin_station": orig,
                "dest_station": dest,
                "station_count": station_diff,
                "duration_minutes": duration_mins,
                "cost": fare,
                "has_interchange": False,
                "lines": [orig.line],
                "interchange_station": None,
            }
        else:
            # Different lines -> interchange at Majestic
            majestic = await MetroRepository.get_station_by_code(db, "MJC")
            if not majestic:
                return None

            leg1_stations = abs(orig.station_order - 6 if orig.line == "purple" else orig.station_order - 9)
            leg2_stations = abs(dest.station_order - 9 if dest.line == "green" else dest.station_order - 6)
            total_stations = leg1_stations + leg2_stations
            duration_mins = round(total_stations * 2.2 + 7.0, 1)  # 5 min transfer at Majestic
            fare = calculate_bmrcl_fare(total_stations)

            return {
                "origin_station": orig,
                "dest_station": dest,
                "station_count": total_stations,
                "duration_minutes": duration_mins,
                "cost": fare,
                "has_interchange": True,
                "lines": [orig.line, dest.line],
                "interchange_station": majestic,
            }

    @staticmethod
    async def get_best_metro_path(
        db: AsyncSession,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        max_station_radius_m: int = 2500,
    ) -> dict | None:
        """Find the most viable metro connection between origin and destination."""
        orig_nearby = await MetroRepository.get_nearby_stations(
            db, origin_lat, origin_lng, radius_m=max_station_radius_m, limit=2
        )
        dest_nearby = await MetroRepository.get_nearby_stations(
            db, dest_lat, dest_lng, radius_m=max_station_radius_m, limit=2
        )

        if not orig_nearby or not dest_nearby:
            return None

        best_orig_entry = orig_nearby[0]
        best_dest_entry = dest_nearby[0]

        orig_st = best_orig_entry["station"]
        dest_st = best_dest_entry["station"]

        if orig_st.code == dest_st.code:
            return None  # Both origin and destination are closest to the exact same station

        route = await MetroService.find_metro_route(db, orig_st.code, dest_st.code)
        if not route:
            return None

        return {
            "origin_station": orig_st,
            "origin_distance_m": best_orig_entry["distance_m"],
            "dest_station": dest_st,
            "dest_distance_m": best_dest_entry["distance_m"],
            "metro_route": route,
        }
