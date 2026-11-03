"""
Fare Analytics and Baseline Price Prediction Service.
"""

import statistics
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fare import FareObservation
from app.schemas.fare import FareHistoryResponse, FarePredictionResponse
from app.schemas.journey import LocationInput


class FareAnalyticsService:
    @staticmethod
    async def get_fare_history(
        db: AsyncSession,
        origin: LocationInput,
        destination: LocationInput,
        provider: str | None = None,
        vehicle_type: str | None = None,
        days: int = 30,
    ) -> FareHistoryResponse:
        tol = 0.03  # Coordinate tolerance (~3km)
        filters = [
            FareObservation.origin_lat.between(origin.latitude - tol, origin.latitude + tol),
            FareObservation.origin_lng.between(origin.longitude - tol, origin.longitude + tol),
            FareObservation.dest_lat.between(destination.latitude - tol, destination.latitude + tol),
            FareObservation.dest_lng.between(destination.longitude - tol, destination.longitude + tol),
        ]
        if provider:
            filters.append(FareObservation.provider == provider)
        if vehicle_type:
            filters.append(FareObservation.vehicle_type == vehicle_type)

        stmt = select(FareObservation).where(and_(*filters)).order_by(FareObservation.observed_at.desc())
        res = await db.execute(stmt)
        obs_list = list(res.scalars().all())

        prov_label = provider or "all_providers"
        veh_label = vehicle_type or "all_vehicles"
        route_label = f"{origin.address or 'Origin'} → {destination.address or 'Destination'}"

        if not obs_list:
            # Fallback when no direct observations are available
            return FareHistoryResponse(
                provider=prov_label,
                vehicle_type=veh_label,
                route=route_label,
                period_days=days,
                sample_count=0,
                average_fare=Decimal("0.00"),
                median_fare=Decimal("0.00"),
                min_fare=Decimal("0.00"),
                max_fare=Decimal("0.00"),
                fare_by_hour={},
                fare_by_day={},
                is_demo_data=True,
                data_sufficient=False,
            )

        fares = [float(o.observed_fare) for o in obs_list]
        avg_f = statistics.mean(fares)
        med_f = statistics.median(fares)
        min_f = min(fares)
        max_f = max(fares)

        hour_map: dict[str, list[float]] = {}
        day_map: dict[str, list[float]] = {}
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        for o in obs_list:
            if o.hour_of_day is not None:
                hr_key = str(o.hour_of_day)
                hour_map.setdefault(hr_key, []).append(float(o.observed_fare))
            if o.day_of_week is not None and 0 <= o.day_of_week < 7:
                day_key = day_names[o.day_of_week]
                day_map.setdefault(day_key, []).append(float(o.observed_fare))

        fare_by_hour = {
            k: Decimal(str(round(statistics.mean(v), 2))) for k, v in hour_map.items()
        }
        fare_by_day = {
            k: Decimal(str(round(statistics.mean(v), 2))) for k, v in day_map.items()
        }

        return FareHistoryResponse(
            provider=prov_label,
            vehicle_type=veh_label,
            route=route_label,
            period_days=days,
            sample_count=len(obs_list),
            average_fare=Decimal(str(round(avg_f, 2))),
            median_fare=Decimal(str(round(med_f, 2))),
            min_fare=Decimal(str(round(min_f, 2))),
            max_fare=Decimal(str(round(max_f, 2))),
            fare_by_hour=fare_by_hour,
            fare_by_day=fare_by_day,
            is_demo_data=any(o.is_demo_data for o in obs_list),
            data_sufficient=len(obs_list) >= 5,
        )

    @staticmethod
    async def predict_fare(
        db: AsyncSession,
        origin: LocationInput,
        destination: LocationInput,
        provider: str = "uber",
        vehicle_type: str = "Uber Go",
    ) -> FarePredictionResponse:
        history = await FareAnalyticsService.get_fare_history(
            db, origin, destination, provider=provider, vehicle_type=vehicle_type, days=30
        )

        now = datetime.now(UTC)
        limitations = [
            "Model is a transparent moving-average baseline with dispersion bounds.",
            "Historical inputs consist of synthetic and observed demo records.",
            "Weather anomalies, live local events, and road closures are not modelled.",
        ]

        if not history.data_sufficient or history.sample_count == 0:
            # Baseline estimation from distance
            from app.providers.demo_providers import get_road_distance_km
            dist_km = max(0.5, get_road_distance_km(origin.latitude, origin.longitude, destination.latitude, destination.longitude))
            base_est = Decimal(str(round(60.0 + (dist_km * 18.0), 2))).quantize(Decimal("1.00"), rounding=ROUND_HALF_UP)
            min_est = (base_est * Decimal("0.90")).quantize(Decimal("1.00"))
            max_est = (base_est * Decimal("1.20")).quantize(Decimal("1.00"))

            return FarePredictionResponse(
                provider=provider,
                vehicle_type=vehicle_type,
                predicted_fare=base_est,
                predicted_min=min_est,
                predicted_max=max_est,
                prediction_timestamp=now,
                training_period_days=30,
                sample_size=0,
                confidence=0.45,
                method="distance_rate_heuristic",
                limitations=[*limitations, "Insufficient historical sample; distance heuristic applied."],
            )

        pred_fare = history.average_fare
        pred_min = (history.min_fare * Decimal("0.95")).quantize(Decimal("1.00"), rounding=ROUND_HALF_UP)
        pred_max = (history.max_fare * Decimal("1.05")).quantize(Decimal("1.00"), rounding=ROUND_HALF_UP)
        conf = min(0.85, 0.50 + (history.sample_count * 0.03))

        return FarePredictionResponse(
            provider=provider,
            vehicle_type=vehicle_type,
            predicted_fare=pred_fare,
            predicted_min=pred_min,
            predicted_max=pred_max,
            prediction_timestamp=now,
            training_period_days=history.period_days,
            sample_size=history.sample_count,
            confidence=round(conf, 2),
            method="weighted_moving_average",
            limitations=limitations,
        )
