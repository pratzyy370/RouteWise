"""
Provider registry for managing and looking up ride providers.
"""

from app.core.config import get_settings
from app.providers.base import BaseProvider
from app.providers.demo_providers import (
    NammaYatriDemoProvider,
    OlaDemoProvider,
    RapidoDemoProvider,
    UberDemoProvider,
)


class ProviderRegistry:
    """Registry maintaining active provider adapter instances."""

    def __init__(self):
        self._providers: dict[str, BaseProvider] = {}

    def register(self, provider: BaseProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> BaseProvider | None:
        return self._providers.get(name)

    def get_all(self) -> list[BaseProvider]:
        return list(self._providers.values())

    async def get_all_statuses(self) -> list[dict]:
        results = []
        for p in self._providers.values():
            status = await p.get_status()
            results.append(
                {
                    "provider": p.name,
                    "display_name": p.display_name,
                    "status": status.value,
                    "demo_mode": not p.is_configured(),
                    "supported_vehicles": p.supported_vehicle_types,
                }
            )
        return results


_registry_instance: ProviderRegistry | None = None


def get_provider_registry() -> ProviderRegistry:
    """Return the global ProviderRegistry initialized with configured or demo providers."""
    global _registry_instance
    if _registry_instance is None:
        settings = get_settings()
        registry = ProviderRegistry()
        registry.register(UberDemoProvider(api_key=settings.UBER_API_KEY))
        registry.register(OlaDemoProvider(api_key=settings.OLA_API_KEY))
        registry.register(RapidoDemoProvider(api_key=settings.RAPIDO_API_KEY))
        registry.register(NammaYatriDemoProvider(api_key=settings.NAMMA_YATRI_API_KEY))
        _registry_instance = registry
    return _registry_instance
