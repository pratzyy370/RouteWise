"""
Trip models – completed trip history and per-user preference storage.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
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


class CompletedTrip(UUIDMixin, Base):
    """A trip that the user has marked as completed (for spending analytics)."""

    __tablename__ = "completed_trips"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    journey_search_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("journey_searches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    origin_lat: Mapped[float] = mapped_column(Float, nullable=False)
    origin_lng: Mapped[float] = mapped_column(Float, nullable=False)
    dest_lat: Mapped[float] = mapped_column(Float, nullable=False)
    dest_lng: Mapped[float] = mapped_column(Float, nullable=False)

    origin_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dest_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    mode: Mapped[str] = mapped_column(String(30), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)

    actual_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    estimated_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    actual_duration_minutes: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    cheapest_alternative_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )

    trip_date: Mapped[date] = mapped_column(Date, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="completed_trips")

    def __repr__(self) -> str:
        return (
            f"<CompletedTrip {self.mode} ₹{self.actual_cost} "
            f"on {self.trip_date}>"
        )


class UserPreference(UUIDMixin, TimestampMixin, Base):
    """Per-user preference settings (one-to-one with User)."""

    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    default_preference: Mapped[str] = mapped_column(
        String(30), default="balanced", nullable=False
    )
    max_walking_distance_m: Mapped[int] = mapped_column(
        Integer, default=1500, nullable=False
    )
    preferred_modes: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # comma-separated: walk,metro,auto,cab
    monthly_budget: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="preference")

    def __repr__(self) -> str:
        return (
            f"<UserPreference pref={self.default_preference!r} "
            f"walk_max={self.max_walking_distance_m}m>"
        )
