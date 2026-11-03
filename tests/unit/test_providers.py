"""
Unit tests for provider adapters and contracts.
"""

from decimal import Decimal

import pytest

from app.providers.base import ProviderStatus, QuoteSource
from app.providers.demo_providers import (
    NammaYatriDemoProvider,
    OlaDemoProvider,
    RapidoDemoProvider,
    UberDemoProvider,
)


@pytest.mark.asyncio
async def test_uber_demo_provider():
    provider = UberDemoProvider()
    assert provider.name == "uber"
    assert await provider.get_status() == ProviderStatus.DEMO
    assert provider.is_configured() is False

    quotes = await provider.get_fare_estimates(12.9784, 77.6385, 12.9756, 77.6066)
    assert len(quotes) >= 2
    for q in quotes:
        assert q.provider == "uber"
        assert q.estimated_fare > Decimal("0")
        assert q.currency == "INR"
        assert q.quote_source == QuoteSource.DEMO
        assert q.booking_url is not None


@pytest.mark.asyncio
async def test_ola_demo_provider():
    provider = OlaDemoProvider()
    quotes = await provider.get_fare_estimates(12.9784, 77.6385, 12.9756, 77.6066)
    assert len(quotes) >= 2
    for q in quotes:
        assert q.provider == "ola"
        assert q.estimated_fare > Decimal("0")


@pytest.mark.asyncio
async def test_rapido_demo_provider():
    provider = RapidoDemoProvider()
    quotes = await provider.get_fare_estimates(12.9784, 77.6385, 12.9756, 77.6066)
    assert len(quotes) == 2
    types = [q.vehicle_type for q in quotes]
    assert "Rapido Bike" in types
    assert "Rapido Auto" in types


@pytest.mark.asyncio
async def test_namma_yatri_demo_provider():
    provider = NammaYatriDemoProvider()
    quotes = await provider.get_fare_estimates(12.9784, 77.6385, 12.9756, 77.6066)
    assert len(quotes) == 2
    types = [q.vehicle_type for q in quotes]
    assert "Namma Yatri Auto" in types
    assert "Namma Yatri Cab" in types
