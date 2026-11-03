"""
Journey models – search requests, multi-modal options, and individual legs.
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

from app.db.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


def _utcnow() -> datetime:
    return datetime.now(UTC)


class JourneySearch(UUIDMixin, Base):
    """A single route-comparison search performed by a user or anonymously."""

    __tablename__ = "journey_searches"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    origin_lat: Mapped[float] = mapped_column(Float, nullable=False)
    origin_lng: Mapped[float] = mapped_column(Float, nullable=False)
    dest_lat: Mapped[float] = mapped_column(Float, nullable=False)
    dest_lng: Mapped[float] = mapped_column(Float, nullable=False)

    origin_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    dest_address: Mapped[str | None] = mapped_column(Text, nullable=True)

    preference: Mapped[str] = mapped_column(
        String(30), nullable=False, default="balanced"
    )  # cheapest / fastest / balanced

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────
    user: Mapped[User | None] = relationship(
        "User", back_populates="journey_searches"
    )
    options: Mapped[list[JourneyOption]] = relationship(
        "JourneyOption",
        back_populates="search",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<JourneySearch ({self.origin_lat},{self.origin_lng}) → "
            f"({self.dest_lat},{self.dest_lng})>"
        )


class JourneyOption(UUIDMixin, Base):
    """One candidate journey returned for a search (may be multi-modal)."""

    __tablename__ = "journey_options"

    search_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("journey_searches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    is_recommended: Mapped[bool] = mapped_column(default=False, nullable=False)

    total_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )
    total_duration_minutes: Mapped[float] = mapped_column(Float, nullable=False)
    total_distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    walking_distance_m: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    transfer_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    recommendation_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────
    search: Mapped[JourneySearch] = relationship(
        "JourneySearch", back_populates="options"
    )
    legs: Mapped[list[JourneyLeg]] = relationship(
        "JourneyLeg",
        back_populates="option",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="JourneyLeg.leg_order",
    )

    def __repr__(self) -> str:
        return (
            f"<JourneyOption rank={self.rank} cost={self.total_cost} "
            f"dur={self.total_duration_minutes}m>"
        )


class JourneyLeg(UUIDMixin, Base):
    """A single leg within a :class:`JourneyOption` (e.g. walk → metro → auto)."""

    __tablename__ = "journey_legs"

    option_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("journey_options.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    leg_order: Mapped[int] = mapped_column(Integer, nullable=False)
    mode: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # walk / metro / auto / cab

    origin_lat: Mapped[float] = mapped_column(Float, nullable=False)
    origin_lng: Mapped[float] = mapped_column(Float, nullable=False)
    dest_lat: Mapped[float] = mapped_column(Float, nullable=False)
    dest_lng: Mapped[float] = mapped_column(Float, nullable=False)

    origin_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dest_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    estimated_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )
    estimated_duration_minutes: Mapped[float] = mapped_column(
        Float, nullable=False
    )
    distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)

    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    data_source: Mapped[str] = mapped_column(
        String(30), nullable=False, default="demo"
    )  # demo / modelled / historical / live
    confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # 0-1

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────
    option: Mapped[JourneyOption] = relationship(
        "JourneyOption", back_populates="legs"
    )

    def __repr__(self) -> str:
        return (
            f"<JourneyLeg #{self.leg_order} {self.mode} "
            f"cost={self.estimated_cost}>"
        )
