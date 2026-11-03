"""
Health check endpoints:
- GET /health/live (Process liveness)
- GET /health/ready (Dependency readiness)
"""

import time

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])
_process_start_time = time.time()


@router.get("/health/live", response_model=HealthResponse)
async def liveness():
    """Liveness probe to confirm that the HTTP worker process is responsive."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        uptime_seconds=round(time.time() - _process_start_time, 1),
        checks={"process": "alive"},
    )


@router.get("/health/ready", response_model=HealthResponse)
async def readiness(db: AsyncSession = Depends(get_db)):
    """Readiness probe checking database connectivity and cache availability."""
    settings = get_settings()
    checks: dict[str, str] = {}
    db_ok = False

    # 1. Database check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ready"
        db_ok = True
    except Exception as e:
        checks["database"] = f"unhealthy: {type(e).__name__}"

    # 2. Redis check (non-blocking fallback)
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=1.0)
        await r.ping()
        checks["redis"] = "ready"
        await r.aclose()
    except Exception:
        checks["redis"] = "unavailable (graceful fallback active)"

    overall_status = "ok" if db_ok else "degraded"
    status_code = status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE

    content = {
        "status": overall_status,
        "version": settings.APP_VERSION,
        "uptime_seconds": round(time.time() - _process_start_time, 1),
        "checks": checks,
    }
    return JSONResponse(status_code=status_code, content=content)
