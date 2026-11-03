"""
Model package – import every ORM model so that ``Base.metadata`` is complete.

Other modules can do ``from app.models import User, SavedPlace, ...`` for
convenience.
"""

from app.models.fare import FareAlert, FareObservation, FareQuote
from app.models.journey import JourneyLeg, JourneyOption, JourneySearch
from app.models.metro import MetroLine, MetroStation
from app.models.place import SavedPlace
from app.models.trip import CompletedTrip, UserPreference
from app.models.user import User

__all__ = [
    "CompletedTrip",
    "FareAlert",
    "FareObservation",
    "FareQuote",
    "JourneyLeg",
    "JourneyOption",
    "JourneySearch",
    "MetroLine",
    "MetroStation",
    "SavedPlace",
    "User",
    "UserPreference",
]
