"""
Fare comparison service.
Concurrently queries all active providers, normalizes quotes, persists observations,
and formats fare comparisons with data provenance.
"""

import asyncio
import logging
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.providers.base import FareEstimate
from app.providers.registry import get_provider_registry
from app.repositories.fare_repo import FareRepository
from app.schemas.journey import FareQuoteResponse

logger = logging.getLogger(__name__)


class FareComparisonService:
    def __init__(self):
        self.registry = get_provider_registry()

    async def _fetch_from_provider(
        self,
        provider_name: str,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
    ) -> list[FareEstimate]:
        provider = self.registry.get(provider_name)
        if not provider:
            return []
        try:
            return await asyncio.wait_for(
                provider.get_fare_estimates(origin_lat, origin_lng, dest_lat, dest_lng),
                timeout=5.0,
            )
        except TimeoutError:
            logger.warning("Provider %s timed out after 5.0s", provider_name)
            return []
        except Exception as e:
            logger.error("Provider %s raised error: %s", provider_name, e)
            return []

    async def compare_fares(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Fetch concurrent quotes across providers, normalize, and sort by estimated fare."""
        providers = self.registry.get_all()
        tasks = [
            self._fetch_from_provider(p.name, origin_lat, origin_lng, dest_lat, dest_lng)
            for p in providers
        ]
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)

        all_estimates: list[FareEstimate] = []
        provider_statuses: dict[str, str] = {}

        for p, res in zip(providers, results_lists):
            if isinstance(res, Exception):
                provider_statuses[p.name] = "error"
            elif not res:
                provider_statuses[p.name] = "no_quotes"
            else:
                provider_statuses[p.name] = "available"
                # Validate quotes: positive fare required
                valid = [est for est in res if est.estimated_fare > Decimal("0")]
                all_estimates.extend(valid)

        # Sort by estimated fare
        all_estimates.sort(key=lambda x: x.estimated_fare)

        # Convert to response objects
        quote_responses: list[FareQuoteResponse] = []
        for est in all_estimates:
            quote_resp = FareQuoteResponse(
                provider=est.provider,
                vehicle_type=est.vehicle_type,
                estimated_fare=est.estimated_fare,
                fare_min=est.fare_min,
                fare_max=est.fare_max,
                currency=est.currency,
                estimated_duration_minutes=est.estimated_duration_minutes,
                distance_m=est.distance_m,
                quote_source=est.quote_source.value,
                quote_status="active",
                surge_multiplier=est.surge_multiplier,
                booking_url=est.booking_url,
                quoted_at=est.quoted_at,
                expires_at=est.expires_at,
            )
            quote_responses.append(quote_resp)

            # Persist to DB if session provided
            if db is not None:
                try:
                    await FareRepository.save_quote(
                        db=db,
                        quote_data={
                            "provider": est.provider,
                            "vehicle_type": est.vehicle_type,
                            "origin_lat": origin_lat,
                            "origin_lng": origin_lng,
                            "dest_lat": dest_lat,
                            "dest_lng": dest_lng,
                            "estimated_fare": est.estimated_fare,
                            "fare_min": est.fare_min,
                            "fare_max": est.fare_max,
                            "currency": est.currency,
                            "estimated_duration_minutes": est.estimated_duration_minutes,
                            "distance_m": est.distance_m,
                            "quote_source": est.quote_source.value,
                            "quote_status": "active",
                            "surge_multiplier": est.surge_multiplier,
                            "booking_url": est.booking_url,
                            "quoted_at": est.quoted_at,
                            "expires_at": est.expires_at,
                        },
                    )
                except Exception as e:
                    logger.debug("Could not persist quote: %s", e)

        return {
            "quotes": quote_responses,
            "provider_status": provider_statuses,
            "total_options": len(quote_responses),
            "data_disclaimer": "All live provider prices are simulated demo estimates. RouteWise does not fabricate live provider availability or booking confirmations.",
        }
