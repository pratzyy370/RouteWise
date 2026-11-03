"""
Database initialization and demo seed CLI script.
Usage:
    python scripts/seed.py
"""

import asyncio
import logging
from app.db.session import async_session_factory, init_db
from app.services.seed_service import SeedService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Initializing database schema...")
    await init_db()
    logger.info("Seeding Bengaluru metro network and demo fare observations...")
    async with async_session_factory() as session:
        await SeedService.seed_metro_data(session)
        await SeedService.seed_demo_observations(session)
    logger.info("Seeding completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())

