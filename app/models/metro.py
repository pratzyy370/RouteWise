"""
Metro models – Namma Metro stations and lines (Bangalore).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin


def _utcnow() -> datetime:
    return datetime.now(UTC)


class MetroStation(UUIDMixin, Base):
    """A Namma Metro station."""

    __tablename__ = "metro_stations"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    line: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # purple / green

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    is_interchange: Mapped[bool] = mapped_column(default=False, nullable=False)
    station_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_operational: Mapped[bool] = mapped_column(default=True, nullable=False)

    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<MetroStation {self.name!r} ({self.code}) line={self.line}>"


class MetroLine(UUIDMixin, Base):
    """A Namma Metro line (e.g. Purple Line, Green Line)."""

    __tablename__ = "metro_lines"

    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )  # Purple Line / Green Line
    code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False
    )  # purple / green
    color: Mapped[str] = mapped_column(String(30), nullable=False)

    total_stations: Mapped[int] = mapped_column(Integer, nullable=False)
    is_operational: Mapped[bool] = mapped_column(default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<MetroLine {self.name!r} stations={self.total_stations}>"
