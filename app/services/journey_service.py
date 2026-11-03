"""
Multimodal Journey Generation and Optimization Service.

Combines direct ride-hailing options (Uber, Ola, Rapido, Namma Yatri) and multimodal
transit options (Walking + Metro + Auto/Cab transfers).
Ranks options according to objective preferences (cheapest, fastest, balanced),
normalizes scoring dimensions, and synthesizes clear, human-readable explanations.
"""

import logging
import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.journey_repo import JourneyRepository
from app.routing.engine import get_routing_engine
from app.schemas.journey import (
    CompareResponse,
    JourneyLegResponse,
    JourneyOptionResponse,
    LocationInput,
)
from app.services.fare_service import FareComparisonService
from app.services.metro_service import MetroService

logger = logging.getLogger(__name__)


class CandidateOption:
    def __init__(self, legs: list[dict], data_freshness: dict[str, str]):
        self.legs = legs
        self.data_freshness = data_freshness

        self.total_cost = sum(leg["estimated_cost"] for leg in legs)
        self.total_duration_minutes = sum(leg["estimated_duration_minutes"] for leg in legs)
        self.total_distance_m = sum(leg["distance_m"] for leg in legs)
        self.walking_distance_m = sum(
            leg["distance_m"] for leg in legs if leg["mode"] == "walk"
        )
        self.transfer_count = max(0, len(legs) - 1)
        self.score: float = 0.0
        self.recommendation_reason: str = ""


class JourneyOptimizationService:
    def __init__(self):
        self.fare_service = FareComparisonService()
        self.routing_engine = get_routing_engine()

    async def optimize_journey(
        self,
        origin: LocationInput,
        destination: LocationInput,
        preference: str = "balanced",
        include_metro: bool = True,
        max_walking_m: int = 1500,
        user_id: uuid.UUID | None = None,
        db: AsyncSession | None = None,
    ) -> CompareResponse:
        candidates: list[CandidateOption] = []

        # 1. Fetch direct ride provider options
        fare_result = await self.fare_service.compare_fares(
            origin.latitude, origin.longitude, destination.latitude, destination.longitude, db=db
        )
        quotes = fare_result["quotes"]

        # Convert direct quotes into candidate options (single-leg journeys)
        for q in quotes:
            leg = {
                "leg_order": 0,
                "mode": "auto" if "auto" in q.vehicle_type.lower() else ("bike" if "bike" in q.vehicle_type.lower() else "cab"),
                "origin_lat": origin.latitude,
                "origin_lng": origin.longitude,
                "origin_name": origin.address or "Pickup Location",
                "dest_lat": destination.latitude,
                "dest_lng": destination.longitude,
                "dest_name": destination.address or "Destination",
                "estimated_cost": q.estimated_fare,
                "estimated_duration_minutes": int(q.estimated_duration_minutes or 25),
                "distance_m": int(q.distance_m or 5000),
                "provider": q.provider,
                "data_source": "demo",
                "confidence": 0.85,
            }
            candidates.append(
                CandidateOption(
                    legs=[leg],
                    data_freshness={q.provider: "demo"},
                )
            )

        # 2. Multimodal Transit options (Walking + Metro + Last-Mile)
        if include_metro and db is not None:
            metro_conn = await MetroService.get_best_metro_path(
                db, origin.latitude, origin.longitude, destination.latitude, destination.longitude
            )
            if metro_conn:
                orig_st = metro_conn["origin_station"]
                dest_st = metro_conn["dest_station"]
                orig_dist_m = metro_conn["origin_distance_m"]
                dest_dist_m = metro_conn["dest_distance_m"]
                m_route = metro_conn["metro_route"]

                # Transit Leg
                metro_leg = {
                    "leg_order": 1,
                    "mode": "metro",
                    "origin_lat": orig_st.latitude,
                    "origin_lng": orig_st.longitude,
                    "origin_name": f"{orig_st.name} Metro Station",
                    "dest_lat": dest_st.latitude,
                    "dest_lng": dest_st.longitude,
                    "dest_name": f"{dest_st.name} Metro Station",
                    "estimated_cost": m_route["cost"],
                    "estimated_duration_minutes": int(m_route["duration_minutes"]),
                    "distance_m": int(m_route["station_count"] * 1200),
                    "provider": "Namma Metro (BMRCL)",
                    "data_source": "modelled",
                    "confidence": 0.95,
                }

                # Multimodal Combo 1: Walk to Metro + Metro + Walk to Dest (if distances <= max_walking_m)
                if orig_dist_m <= max_walking_m and dest_dist_m <= max_walking_m:
                    walk_orig = {
                        "leg_order": 0,
                        "mode": "walk",
                        "origin_lat": origin.latitude,
                        "origin_lng": origin.longitude,
                        "origin_name": origin.address or "Pickup Location",
                        "dest_lat": orig_st.latitude,
                        "dest_lng": orig_st.longitude,
                        "dest_name": f"{orig_st.name} Metro Station",
                        "estimated_cost": Decimal("0.00"),
                        "estimated_duration_minutes": max(1, int((orig_dist_m / 1000.0 / 4.5) * 60)),
                        "distance_m": int(orig_dist_m),
                        "provider": None,
                        "data_source": "modelled",
                        "confidence": 1.0,
                    }
                    walk_dest = {
                        "leg_order": 2,
                        "mode": "walk",
                        "origin_lat": dest_st.latitude,
                        "origin_lng": dest_st.longitude,
                        "origin_name": f"{dest_st.name} Metro Station",
                        "dest_lat": destination.latitude,
                        "dest_lng": destination.longitude,
                        "dest_name": destination.address or "Destination",
                        "estimated_cost": Decimal("0.00"),
                        "estimated_duration_minutes": max(1, int((dest_dist_m / 1000.0 / 4.5) * 60)),
                        "distance_m": int(dest_dist_m),
                        "provider": None,
                        "data_source": "modelled",
                        "confidence": 1.0,
                    }
                    candidates.append(
                        CandidateOption(
                            legs=[walk_orig, metro_leg, walk_dest],
                            data_freshness={"metro": "static_fare_table", "walk": "modelled"},
                        )
                    )

                # Multimodal Combo 2: Auto to Metro + Metro + Walk to Dest
                if dest_dist_m <= max_walking_m:
                    first_mile_auto_fare = Decimal(str(max(30, int(30 + (orig_dist_m / 1000.0) * 14))))
                    auto_orig = {
                        "leg_order": 0,
                        "mode": "auto",
                        "origin_lat": origin.latitude,
                        "origin_lng": origin.longitude,
                        "origin_name": origin.address or "Pickup Location",
                        "dest_lat": orig_st.latitude,
                        "dest_lng": orig_st.longitude,
                        "dest_name": f"{orig_st.name} Metro Station",
                        "estimated_cost": first_mile_auto_fare,
                        "estimated_duration_minutes": max(4, int((orig_dist_m / 1000.0 / 18.0) * 60 + 3)),
                        "distance_m": int(orig_dist_m),
                        "provider": "Namma Yatri Auto (First Mile)",
                        "data_source": "demo",
                        "confidence": 0.85,
                    }
                    walk_dest = {
                        "leg_order": 2,
                        "mode": "walk",
                        "origin_lat": dest_st.latitude,
                        "origin_lng": dest_st.longitude,
                        "origin_name": f"{dest_st.name} Metro Station",
                        "dest_lat": destination.latitude,
                        "dest_lng": destination.longitude,
                        "dest_name": destination.address or "Destination",
                        "estimated_cost": Decimal("0.00"),
                        "estimated_duration_minutes": max(1, int((dest_dist_m / 1000.0 / 4.5) * 60)),
                        "distance_m": int(dest_dist_m),
                        "provider": None,
                        "data_source": "modelled",
                        "confidence": 1.0,
                    }
                    candidates.append(
                        CandidateOption(
                            legs=[auto_orig, metro_leg, walk_dest],
                            data_freshness={"namma_yatri": "demo", "metro": "static_fare_table", "walk": "modelled"},
                        )
                    )

        if not candidates:
            # Fallback direct walk if very close
            walk_dist = 500
            candidates.append(
                CandidateOption(
                    legs=[{
                        "leg_order": 0,
                        "mode": "walk",
                        "origin_lat": origin.latitude,
                        "origin_lng": origin.longitude,
                        "origin_name": origin.address or "Origin",
                        "dest_lat": destination.latitude,
                        "dest_lng": destination.longitude,
                        "dest_name": destination.address or "Destination",
                        "estimated_cost": Decimal("0.00"),
                        "estimated_duration_minutes": 10,
                        "distance_m": walk_dist,
                        "provider": None,
                        "data_source": "modelled",
                        "confidence": 1.0,
                    }],
                    data_freshness={"walk": "modelled"},
                )
            )

        # 3. Normalized multi-objective scoring
        min_cost = min(c.total_cost for c in candidates)
        max_cost = max(c.total_cost for c in candidates)
        cost_range = float(max_cost - min_cost) if max_cost > min_cost else 1.0

        min_dur = min(c.total_duration_minutes for c in candidates)
        max_dur = max(c.total_duration_minutes for c in candidates)
        dur_range = float(max_dur - min_dur) if max_dur > min_dur else 1.0

        min_walk = min(c.walking_distance_m for c in candidates)
        max_walk = max(c.walking_distance_m for c in candidates)
        walk_range = float(max_walk - min_walk) if max_walk > min_walk else 1.0

        # Preference weights:
        # Lower score = better option
        if preference == "cheapest":
            w_cost, w_dur, w_walk, w_trans = 0.70, 0.15, 0.10, 0.05
        elif preference == "fastest":
            w_cost, w_dur, w_walk, w_trans = 0.10, 0.70, 0.10, 0.10
        else:  # balanced
            w_cost, w_dur, w_walk, w_trans = 0.40, 0.35, 0.15, 0.10

        for c in candidates:
            norm_cost = float(c.total_cost - min_cost) / cost_range
            norm_dur = float(c.total_duration_minutes - min_dur) / dur_range
            norm_walk = float(c.walking_distance_m - min_walk) / walk_range
            norm_trans = min(1.0, c.transfer_count * 0.5)

            # Raw penalty score
            raw_penalty = (
                w_cost * norm_cost
                + w_dur * norm_dur
                + w_walk * norm_walk
                + w_trans * norm_trans
            )
            # Invert so higher score is better (for UI 0-100 scale)
            c.score = round(max(0.0, (1.0 - raw_penalty) * 100), 1)

        # Sort descending by score
        candidates.sort(key=lambda x: x.score, reverse=True)

        cheapest_option = min(candidates, key=lambda x: x.total_cost)
        fastest_option = min(candidates, key=lambda x: x.total_duration_minutes)

        # Generate explainable reasoning for each candidate
        for c in candidates:
            reasons = []
            if c is cheapest_option:
                extra_time = c.total_duration_minutes - fastest_option.total_duration_minutes
                if extra_time > 0:
                    reasons.append(
                        f"Recommended because this option has the lowest estimated cost (₹{c.total_cost}). "
                        f"It may take {extra_time} mins longer than the fastest option."
                    )
                else:
                    reasons.append(
                        f"Optimal pick: Lowest cost (₹{c.total_cost}) and fastest journey ({c.total_duration_minutes} mins)."
                    )
            elif c is fastest_option:
                extra_cost = c.total_cost - cheapest_option.total_cost
                if extra_cost > Decimal("0"):
                    reasons.append(
                        f"Recommended as the fastest option at {c.total_duration_minutes} mins. "
                        f"It costs ₹{extra_cost} more than the cheapest option."
                    )
                else:
                    reasons.append(
                        f"Recommended as the fastest journey at {c.total_duration_minutes} mins."
                    )
            else:
                has_metro = any(leg["mode"] == "metro" for leg in c.legs)
                if has_metro:
                    reasons.append(
                        f"Balanced multimodal route combining metro and last-mile connectivity. "
                        f"Saves money (₹{c.total_cost}) with predictable transit timings."
                    )
                else:
                    reasons.append(
                        f"Convenient door-to-door direct option (₹{c.total_cost}, {c.total_duration_minutes} mins) "
                        f"with zero transit transfers."
                    )
            c.recommendation_reason = " ".join(reasons)

        # Save to database if db session provided
        search_id = uuid.uuid4()
        if db is not None:
            try:
                search_rec = await JourneyRepository.create_search(
                    db,
                    {
                        "user_id": user_id,
                        "origin_lat": origin.latitude,
                        "origin_lng": origin.longitude,
                        "dest_lat": destination.latitude,
                        "dest_lng": destination.longitude,
                        "origin_address": origin.address,
                        "dest_address": destination.address,
                        "preference": preference,
                    },
                )
                search_id = search_rec.id

                for idx, c in enumerate(candidates):
                    opt_rec = await JourneyRepository.create_option(
                        db,
                        {
                            "search_id": search_id,
                            "rank": idx + 1,
                            "is_recommended": (idx == 0),
                            "total_cost": c.total_cost,
                            "total_duration_minutes": c.total_duration_minutes,
                            "total_distance_m": c.total_distance_m,
                            "walking_distance_m": c.walking_distance_m,
                            "transfer_count": c.transfer_count,
                            "score": c.score,
                            "recommendation_reason": c.recommendation_reason,
                        },
                    )
                    for leg in c.legs:
                        await JourneyRepository.create_leg(
                            db,
                            {
                                "option_id": opt_rec.id,
                                "leg_order": leg["leg_order"],
                                "mode": leg["mode"],
                                "origin_lat": leg["origin_lat"],
                                "origin_lng": leg["origin_lng"],
                                "origin_name": leg["origin_name"],
                                "dest_lat": leg["dest_lat"],
                                "dest_lng": leg["dest_lng"],
                                "dest_name": leg["dest_name"],
                                "estimated_cost": leg["estimated_cost"],
                                "estimated_duration_minutes": leg["estimated_duration_minutes"],
                                "distance_m": leg["distance_m"],
                                "provider": leg["provider"],
                                "data_source": leg["data_source"],
                                "confidence": leg["confidence"],
                            },
                        )
                await db.commit()
            except Exception as e:
                logger.error("Failed to persist journey options: %s", e)

        # Build schema responses
        def build_option_response(c: CandidateOption, rank: int, is_rec: bool) -> JourneyOptionResponse:
            legs_resp = [
                JourneyLegResponse(
                    leg_order=leg["leg_order"],
                    mode=leg["mode"],
                    origin_lat=leg["origin_lat"],
                    origin_lng=leg["origin_lng"],
                    origin_name=leg["origin_name"],
                    dest_lat=leg["dest_lat"],
                    dest_lng=leg["dest_lng"],
                    dest_name=leg["dest_name"],
                    estimated_cost=leg["estimated_cost"],
                    estimated_duration_minutes=int(leg["estimated_duration_minutes"]),
                    distance_m=int(leg["distance_m"]),
                    provider=leg["provider"],
                    data_source=leg["data_source"],
                    confidence=leg["confidence"],
                )
                for leg in c.legs
            ]
            return JourneyOptionResponse(
                id=uuid.uuid4(),
                rank=rank,
                is_recommended=is_rec,
                total_cost=c.total_cost,
                total_duration_minutes=int(c.total_duration_minutes),
                total_distance_m=int(c.total_distance_m),
                walking_distance_m=int(c.walking_distance_m),
                transfer_count=c.transfer_count,
                score=c.score,
                recommendation_reason=c.recommendation_reason,
                legs=legs_resp,
                data_freshness=c.data_freshness,
            )

        recommended = build_option_response(candidates[0], rank=1, is_rec=True)
        alternatives = [
            build_option_response(c, rank=i + 2, is_rec=False)
            for i, c in enumerate(candidates[1:6])  # Return top 5 alternatives
        ]

        return CompareResponse(
            search_id=search_id,
            recommended=recommended,
            alternatives=alternatives,
            provider_status=fare_result["provider_status"],
            data_disclaimer=(
                "All provider fares, transit routes, and walking distances are simulated estimates "
                "or modelled transit figures for Bengaluru. RouteWise does not fabricate live provider "
                "availability or train schedules."
            ),
        )
