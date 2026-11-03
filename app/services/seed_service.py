"""
Seed service for Bengaluru Metro lines and stations, and initial fare observations.
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fare import FareObservation
from app.models.metro import MetroLine, MetroStation

logger = logging.getLogger(__name__)


# Standard Namma Metro lines and selected stations with approximate coordinates
PURPLE_LINE_STATIONS = [
    ("Challaghatta", "CHG", 12.9038, 77.4722, False, 1),
    ("Kengeri", "KGI", 12.9130, 77.4835, False, 2),
    ("Rajarajeshwari Nagar", "RRN", 12.9348, 77.5186, False, 3),
    ("Mysuru Road", "MSR", 12.9482, 77.5381, False, 4),
    ("Vijayanagar", "VJN", 12.9698, 77.5372, False, 5),
    ("Nadaprabhu Kempegowda Majestic", "MJC", 12.9757, 77.5728, True, 6),
    ("Sir M. Visveshwaraya Central College", "SVC", 12.9744, 77.5847, False, 7),
    ("Vidhana Soudha", "VSD", 12.9796, 77.5925, False, 8),
    ("Cubbon Park", "CBP", 12.9811, 77.5994, False, 9),
    ("MG Road", "MGR", 12.9756, 77.6066, False, 10),
    ("Trinity", "TRN", 12.9729, 77.6171, False, 11),
    ("Halasuru", "HLS", 12.9760, 77.6265, False, 12),
    ("Indiranagar", "IDN", 12.9784, 77.6385, False, 13),
    ("Swami Vivekananda Road", "SVR", 12.9860, 77.6444, False, 14),
    ("Baiyappanahalli", "BYP", 12.9912, 77.6525, False, 15),
    ("KR Pura", "KRP", 12.9986, 77.6888, False, 16),
    ("Whitefield (Kadugodi)", "WFD", 12.9961, 77.7610, False, 17),
]

GREEN_LINE_STATIONS = [
    ("Nagasandra", "NGS", 13.0478, 77.5002, False, 1),
    ("Dasarahalli", "DSH", 13.0435, 77.5126, False, 2),
    ("Jalahalli", "JLH", 13.0392, 77.5197, False, 3),
    ("Peenya", "PNY", 13.0331, 77.5259, False, 4),
    ("Goraguntepalya", "GGP", 13.0282, 77.5393, False, 5),
    ("Yeshwanthpur", "YPR", 13.0232, 77.5502, False, 6),
    ("Rajajinagar", "RJN", 12.9990, 77.5559, False, 7),
    ("Kuvempu Road", "KVR", 12.9904, 77.5593, False, 8),
    ("Nadaprabhu Kempegowda Majestic", "MJC", 12.9757, 77.5728, True, 9),
    ("Chickpete", "CKP", 12.9680, 77.5750, False, 10),
    ("Krishna Rajendra Market", "KRM", 12.9610, 77.5744, False, 11),
    ("National College", "NLC", 12.9515, 77.5735, False, 12),
    ("Lalbagh", "LBG", 12.9463, 77.5800, False, 13),
    ("South End Circle", "SEC", 12.9382, 77.5802, False, 14),
    ("Jayanagar", "JYN", 12.9304, 77.5803, False, 15),
    ("Rashtreeya Vidyalaya Road", "RVR", 12.9216, 77.5801, False, 16),
    ("Banashankari", "BSK", 12.9152, 77.5736, False, 17),
    ("JP Nagar", "JPN", 12.9073, 77.5731, False, 18),
    ("Yelachenahalli", "YCH", 12.8958, 77.5709, False, 19),
    ("Silk Institute", "SKI", 12.8625, 77.5458, False, 20),
]


class SeedService:
    @staticmethod
    async def seed_metro_data(db: AsyncSession) -> None:
        """Seed Namma Metro lines and stations if not already present."""
        # Check if stations exist
        existing = await db.execute(select(MetroStation).limit(1))
        if existing.scalar_one_or_none() is not None:
            logger.info("Metro stations already present in database.")
            return

        # Seed lines
        purple_line = MetroLine(
            name="Purple Line",
            code="purple",
            color="#800080",
            total_stations=len(PURPLE_LINE_STATIONS),
        )
        green_line = MetroLine(
            name="Green Line",
            code="green",
            color="#008000",
            total_stations=len(GREEN_LINE_STATIONS),
        )
        db.add_all([purple_line, green_line])

        # Seed stations
        station_codes_seen: set[str] = set()

        for name, code, lat, lng, is_interchange, order in PURPLE_LINE_STATIONS:
            if code in station_codes_seen:
                continue
            station_codes_seen.add(code)
            station = MetroStation(
                name=name,
                code=code,
                line="purple",
                latitude=lat,
                longitude=lng,
                is_interchange=is_interchange,
                station_order=order,
                is_operational=True,
                address=f"{name}, Bengaluru, Karnataka",
            )
            db.add(station)

        for name, code, lat, lng, is_interchange, order in GREEN_LINE_STATIONS:
            if code in station_codes_seen:
                continue
            station_codes_seen.add(code)
            station = MetroStation(
                name=name,
                code=code,
                line="green",
                latitude=lat,
                longitude=lng,
                is_interchange=is_interchange,
                station_order=order,
                is_operational=True,
                address=f"{name}, Bengaluru, Karnataka",
            )
            db.add(station)

        await db.commit()
        logger.info("Seeded %d metro stations.", len(station_codes_seen))

    @staticmethod
    async def seed_demo_observations(db: AsyncSession) -> None:
        """Seed initial realistic demo observations across providers."""
        existing = await db.execute(select(FareObservation).limit(1))
        if existing.scalar_one_or_none() is not None:
            return

        # Pre-seed observations around Indiranagar to MG Road, and Majestic to Whitefield
        routes = [
            # Indiranagar to MG Road (~4 km)
            (12.9784, 77.6385, 12.9756, 77.6066, [
                ("uber", "Uber Auto", 75, 14, 1),
                ("uber", "Uber Go", 130, 14, 1),
                ("ola", "Ola Auto", 70, 14, 1),
                ("ola", "Ola Mini", 125, 14, 1),
                ("rapido", "Rapido Bike", 48, 14, 1),
                ("rapido", "Rapido Auto", 68, 14, 1),
                ("namma_yatri", "Namma Yatri Auto", 65, 14, 1),
                ("namma_yatri", "Namma Yatri Cab", 115, 14, 1),
            ]),
            # Koramangala to Whitefield (~18 km)
            (12.9352, 77.6245, 12.9961, 77.7610, [
                ("uber", "Uber Auto", 290, 9, 2),
                ("uber", "Uber Go", 450, 9, 2),
                ("ola", "Ola Auto", 280, 9, 2),
                ("ola", "Ola Mini", 440, 9, 2),
                ("rapido", "Rapido Bike", 175, 9, 2),
                ("rapido", "Rapido Auto", 270, 9, 2),
                ("namma_yatri", "Namma Yatri Auto", 260, 9, 2),
                ("namma_yatri", "Namma Yatri Cab", 410, 9, 2),
            ]),
            # Majestic to Jayanagar (~7 km)
            (12.9757, 77.5728, 12.9304, 77.5803, [
                ("uber", "Uber Auto", 120, 18, 3),
                ("uber", "Uber Go", 210, 18, 3),
                ("ola", "Ola Auto", 115, 18, 3),
                ("ola", "Ola Mini", 200, 18, 3),
                ("rapido", "Rapido Bike", 75, 18, 3),
                ("rapido", "Rapido Auto", 110, 18, 3),
                ("namma_yatri", "Namma Yatri Auto", 105, 18, 3),
                ("namma_yatri", "Namma Yatri Cab", 190, 18, 3),
            ]),
        ]

        now = datetime.now(UTC)
        observations = []
        for orig_lat, orig_lng, dst_lat, dst_lng, data_points in routes:
            for prov, v_type, fare, hr, dow in data_points:
                # Add multiple samples with small variation
                for diff in [-5, 0, 8, -2, 12]:
                    f_val = Decimal(str(max(20, fare + diff)))
                    observations.append(
                        FareObservation(
                            provider=prov,
                            vehicle_type=v_type,
                            origin_lat=orig_lat,
                            origin_lng=orig_lng,
                            dest_lat=dst_lat,
                            dest_lng=dst_lng,
                            observed_fare=f_val,
                            currency="INR",
                            is_demo_data=True,
                            hour_of_day=hr,
                            day_of_week=dow,
                            observed_at=now,
                        )
                    )

        db.add_all(observations)
        await db.commit()
        logger.info("Seeded %d demo fare observations.", len(observations))
