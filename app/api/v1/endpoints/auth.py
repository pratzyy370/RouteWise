"""
Authentication and user endpoints.
"""

from datetime import timedelta

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.security import create_access_token, create_refresh_token, decode_token, pwd_hasher
from app.repositories.user_repo import UserRepository
from app.schemas.auth import TokenResponse, UserLogin, UserRegister, UserResponse, UserUpdate

router = APIRouter(tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db: DbSession):
    """Register a new user account with unique email address."""
    existing = await UserRepository.get_by_email(db, payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    user = await UserRepository.create(
        db,
        {
            "email": payload.email,
            "password": payload.password,
            "full_name": payload.full_name,
            "role": "user",
            "is_active": True,
            "is_verified": False,
        },
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: DbSession):
    """Authenticate with email and password and receive JWT tokens."""
    user = await UserRepository.get_by_email(db, payload.email)
    if not user or not pwd_hasher.verify(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    settings = get_settings()
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role},
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(token: str, db: DbSession):
    """Obtain a new access token using a valid refresh token."""
    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    from uuid import UUID
    user = await UserRepository.get_by_id(db, UUID(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    settings = get_settings()
    new_access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role},
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    new_refresh_token = create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    """Retrieve the profile of the currently authenticated user."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_me(payload: UserUpdate, current_user: CurrentUser, db: DbSession):
    """Update profile details for the current user."""
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_data:
        return current_user

    if "email" in update_data and update_data["email"] != current_user.email:
        existing = await UserRepository.get_by_email(db, update_data["email"])
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already taken")

    updated = await UserRepository.update(db, current_user.id, update_data)
    await db.commit()
    return updated
