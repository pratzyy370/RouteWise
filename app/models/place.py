"""
SavedPlace model – user-bookmarked locations (home, work, college, etc.).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class SavedPlace(UUIDMixin, TimestampMixin, Base):
    """A user-bookmarked geographic location."""

    __tablename__ = "saved_places"

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_saved_places_user_name"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    label: Mapped[str] = mapped_column(
        String(50), nullable=False, default="other"
    )  # home / work / college / other
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="saved_places")

    def __repr__(self) -> str:
        return f"<SavedPlace {self.name!r} label={self.label!r}>"
