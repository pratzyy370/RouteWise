"""
User preferences endpoint for commuting goals and constraints.
"""

from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DbSession
from app.models.trip import UserPreference

router = APIRouter(tags=["Preferences"])


class UserPreferenceSchema(BaseModel):
    default_preference: str = Field("balanced", description="cheapest / fastest / balanced")
    max_walking_distance_m: int = Field(1500, ge=100, le=5000)
    preferred_modes: str | None = Field(None, description="Comma-separated: walk,metro,auto,cab")
    monthly_budget: Decimal | None = None

    model_config = {"from_attributes": True}


@router.get("", response_model=UserPreferenceSchema)
async def get_preferences(current_user: CurrentUser, db: DbSession):
    """Retrieve commuting preferences for the current user."""
    stmt = select(UserPreference).where(UserPreference.user_id == current_user.id)
    res = await db.execute(stmt)
    pref = res.scalar_one_or_none()
    if not pref:
        # Default settings
        return UserPreferenceSchema()
    return pref


@router.put("", response_model=UserPreferenceSchema)
async def update_preferences(
    payload: UserPreferenceSchema,
    current_user: CurrentUser,
    db: DbSession,
):
    """Update commuting preferences for the current user."""
    stmt = select(UserPreference).where(UserPreference.user_id == current_user.id)
    res = await db.execute(stmt)
    pref = res.scalar_one_or_none()

    if not pref:
        pref = UserPreference(
            user_id=current_user.id,
            default_preference=payload.default_preference,
            max_walking_distance_m=payload.max_walking_distance_m,
            preferred_modes=payload.preferred_modes,
            monthly_budget=payload.monthly_budget,
        )
        db.add(pref)
    else:
        pref.default_preference = payload.default_preference
        pref.max_walking_distance_m = payload.max_walking_distance_m
        pref.preferred_modes = payload.preferred_modes
        pref.monthly_budget = payload.monthly_budget

    await db.commit()
    await db.refresh(pref)
    return pref
