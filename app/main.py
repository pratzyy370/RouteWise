"""
RouteWise — Bengaluru Smart Urban Mobility Platform
FastAPI Application Entry Point.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.v1.endpoints import health
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import RouteWiseError
from app.core.logging import configure_logging
from app.db.session import async_session_factory, init_db
from app.middleware.error_handler import (
    generic_error_handler,
    routewise_error_handler,
    validation_error_handler,
)
from app.middleware.request_id import RequestIDMiddleware
from app.services.seed_service import SeedService

settings = get_settings()
configure_logging(debug=settings.DEBUG)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown hooks."""
    logger.info("Starting up %s v%s in %s mode...", settings.APP_NAME, settings.APP_VERSION, "demo" if settings.DEMO_MODE else "production")

    # 1. Initialize tables (dev / sqlite fallback)
    try:
        await init_db()
        logger.info("Database schema initialized.")
    except Exception as e:
        logger.warning("Could not auto-initialize tables: %s", e)

    # 2. Seed Bengaluru metro network and initial observations
    try:
        async with async_session_factory() as session:
            await SeedService.seed_metro_data(session)
            await SeedService.seed_demo_observations(session)
            logger.info("Seeded initial Bengaluru metro network and demo fare observations.")
    except Exception as e:
        logger.warning("Could not seed demo records: %s", e)

    yield

    logger.info("Shutting down %s gracefully...", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    description="Bengaluru-first smart urban mobility platform comparing ride services and recommending multimodal journeys.",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── Middlewares ──────────────────────────────────────────────────────────────
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception Handlers ───────────────────────────────────────────────────────
app.add_exception_handler(RouteWiseError, routewise_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, generic_error_handler)

# ── Static Files & Templates ────────────────────────────────────────────────
static_path = BASE_DIR / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# ── Health Endpoints (Accessible at Root Level) ───────────────────────────────
app.include_router(health.router)

# ── API v1 Router ────────────────────────────────────────────────────────────
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# ── Frontend Web UI Route ────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse, tags=["Frontend"])
async def render_frontend(request: Request):
    """Serve the minimal, responsive RouteWise web dashboard."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "demo_mode": settings.DEMO_MODE,
        },
    )
