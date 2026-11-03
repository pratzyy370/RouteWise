"""
User model – authentication, profile, and role management.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.fare import FareAlert
    from app.models.journey import JourneySearch
    from app.models.place import SavedPlace
    from app.models.trip import CompletedTrip, UserPreference


class User(UUIDMixin, TimestampMixin, Base):
    """Application user account."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(320), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(1024), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), default="user", nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────
    saved_places: Mapped[list[SavedPlace]] = relationship(
        "SavedPlace",
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    journey_searches: Mapped[list[JourneySearch]] = relationship(
        "JourneySearch",
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    completed_trips: Mapped[list[CompletedTrip]] = relationship(
        "CompletedTrip",
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    fare_alerts: Mapped[list[FareAlert]] = relationship(
        "FareAlert",
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    preference: Mapped[UserPreference | None] = relationship(
        "UserPreference",
        back_populates="user",
        lazy="selectin",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User {self.email!r} id={self.id}>"
