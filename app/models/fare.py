"""
Fare models – real-time quotes, historical observations, and price alerts.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


def _utcnow() -> datetime:
    return datetime.now(UTC)


class FareQuote(UUIDMixin, Base):
    """A point-in-time fare estimate from a mobility provider."""

    __tablename__ = "fare_quotes"

    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    vehicle_type: Mapped[str] = mapped_column(String(50), nullable=False)

    origin_lat: Mapped[float] = mapped_column(Float, nullable=False)
    origin_lng: Mapped[float] = mapped_column(Float, nullable=False)
    dest_lat: Mapped[float] = mapped_column(Float, nullable=False)
    dest_lng: Mapped[float] = mapped_column(Float, nullable=False)

    estimated_fare: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    fare_min: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    fare_max: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)

    estimated_duration_minutes: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)

    quote_source: Mapped[str] = mapped_column(
        String(30), nullable=False, default="demo"
    )  # demo / live / cached / modelled
    quote_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )  # active / expired / error

    surge_multiplier: Mapped[float | None] = mapped_column(
        Float, nullable=True, default=1.0
    )
    booking_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    quoted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<FareQuote {self.provider}/{self.vehicle_type} "
            f"₹{self.estimated_fare}>"
        )


class FareObservation(UUIDMixin, Base):
    """A recorded historical fare data point (live-scraped or demo-seeded)."""

    __tablename__ = "fare_observations"

    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    vehicle_type: Mapped[str] = mapped_column(String(50), nullable=False)

    origin_lat: Mapped[float] = mapped_column(Float, nullable=False)
    origin_lng: Mapped[float] = mapped_column(Float, nullable=False)
    dest_lat: Mapped[float] = mapped_column(Float, nullable=False)
    dest_lng: Mapped[float] = mapped_column(Float, nullable=False)

    observed_fare: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)

    is_demo_data: Mapped[bool] = mapped_column(default=True, nullable=False)

    hour_of_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True)

    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<FareObservation {self.provider}/{self.vehicle_type} "
            f"₹{self.observed_fare} @ {self.observed_at}>"
        )


class FareAlert(UUIDMixin, TimestampMixin, Base):
    """User-configured alert triggered when a fare drops below a target."""

    __tablename__ = "fare_alerts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    origin_lat: Mapped[float] = mapped_column(Float, nullable=False)
    origin_lng: Mapped[float] = mapped_column(Float, nullable=False)
    dest_lat: Mapped[float] = mapped_column(Float, nullable=False)
    dest_lng: Mapped[float] = mapped_column(Float, nullable=False)

    origin_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dest_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    vehicle_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    target_fare: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    last_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cooldown_minutes: Mapped[int] = mapped_column(
        Integer, default=60, nullable=False
    )
    notification_method: Mapped[str] = mapped_column(
        String(30), default="log", nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="fare_alerts")

    def __repr__(self) -> str:
        return (
            f"<FareAlert target=₹{self.target_fare} "
            f"active={self.is_active}>"
        )
