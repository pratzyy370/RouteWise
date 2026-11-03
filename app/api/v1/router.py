"""
Main v1 API router assembling all domain routes.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    fares,
    health,
    journeys,
    metro,
    places,
    preferences,
    providers,
    trips,
)

api_router = APIRouter()

# Health endpoints mounted directly
api_router.include_router(health.router)

# Domain routes with appropriate prefixes
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(journeys.router, prefix="/journeys", tags=["Journeys"])
api_router.include_router(metro.router, prefix="/metro", tags=["Metro"])
api_router.include_router(providers.router, prefix="/providers", tags=["Providers"])
api_router.include_router(places.router, prefix="/places", tags=["Places"])
api_router.include_router(fares.router, prefix="/fares", tags=["Fares"])
api_router.include_router(trips.router, prefix="/trips", tags=["Trips"])
api_router.include_router(preferences.router, prefix="/preferences", tags=["Preferences"])
