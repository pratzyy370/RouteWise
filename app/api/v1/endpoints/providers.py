"""
Provider status and integration health endpoint.
"""

from fastapi import APIRouter

from app.providers.registry import get_provider_registry

router = APIRouter(tags=["Providers"])


@router.get("/status")
async def get_providers_status():
    """
    Return operational and configuration status of ride providers.
    Explicitly indicates whether each provider is running with verified live credentials
    or in transparent synthetic demo mode.
    """
    registry = get_provider_registry()
    statuses = await registry.get_all_statuses()
    return {
        "providers": statuses,
        "mode": "demo",
        "notice": (
            "All providers are currently operating in deterministic demo mode. "
            "Live provider credentials can be configured via environment variables."
        ),
    }
