"""
Saved Places CRUD endpoints with strict user ownership enforcement.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUser, DbSession
from app.repositories.place_repo import PlaceRepository
from app.schemas.place import PlaceCreate, PlaceResponse, PlaceUpdate

router = APIRouter(tags=["Places"])


@router.get("", response_model=list[PlaceResponse])
async def list_places(current_user: CurrentUser, db: DbSession):
    """Retrieve all saved places belonging to the authenticated user."""
    return await PlaceRepository.get_user_places(db, current_user.id)


@router.post("", response_model=PlaceResponse, status_code=status.HTTP_201_CREATED)
async def create_place(payload: PlaceCreate, current_user: CurrentUser, db: DbSession):
    """Create a new saved place (Home, Work, College, or Custom)."""
    place = await PlaceRepository.create(
        db,
        current_user.id,
        {
            "name": payload.name,
            "label": payload.label,
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "address": payload.address,
        },
    )
    await db.commit()
    await db.refresh(place)
    return place


@router.patch("/{place_id}", response_model=PlaceResponse)
async def update_place(
    place_id: UUID,
    payload: PlaceUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Update a saved place. Verifies user ownership."""
    existing = await PlaceRepository.get_by_id(db, place_id, user_id=current_user.id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Place not found or does not belong to you",
        )

    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_data:
        return existing

    updated = await PlaceRepository.update(db, place_id, update_data, user_id=current_user.id)
    await db.commit()
    return updated


@router.delete("/{place_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_place(
    place_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """Delete a saved place. Verifies user ownership."""
    deleted = await PlaceRepository.delete(db, place_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Place not found or does not belong to you",
        )
    await db.commit()
    return None
