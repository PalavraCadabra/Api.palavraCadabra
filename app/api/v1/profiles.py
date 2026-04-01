import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.models.aac_profile import AACProfile
from app.schemas.aac_profile import AACProfileCreate, AACProfileRead, AACProfileUpdate

router = APIRouter()


@router.post("/", response_model=AACProfileRead, status_code=status.HTTP_201_CREATED)
async def create_profile(
    data: AACProfileCreate,
    session: DBSession,
    current_user: CurrentUser,
) -> AACProfile:
    profile = AACProfile(user_id=current_user.id, **data.model_dump())
    session.add(profile)
    await session.flush()
    await session.refresh(profile)
    return profile


@router.get("/", response_model=list[AACProfileRead])
async def list_profiles(
    session: DBSession,
    current_user: CurrentUser,
) -> list[AACProfile]:
    result = await session.execute(
        select(AACProfile).where(AACProfile.user_id == current_user.id)
    )
    return list(result.scalars().all())


@router.get("/{profile_id}", response_model=AACProfileRead)
async def get_profile(
    profile_id: uuid.UUID,
    session: DBSession,
    current_user: CurrentUser,
) -> AACProfile:
    result = await session.execute(
        select(AACProfile).where(
            AACProfile.id == profile_id,
            AACProfile.user_id == current_user.id,
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile


@router.patch("/{profile_id}", response_model=AACProfileRead)
async def update_profile(
    profile_id: uuid.UUID,
    data: AACProfileUpdate,
    session: DBSession,
    current_user: CurrentUser,
) -> AACProfile:
    result = await session.execute(
        select(AACProfile).where(
            AACProfile.id == profile_id,
            AACProfile.user_id == current_user.id,
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    await session.flush()
    await session.refresh(profile)
    return profile


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: uuid.UUID,
    session: DBSession,
    current_user: CurrentUser,
) -> None:
    result = await session.execute(
        select(AACProfile).where(
            AACProfile.id == profile_id,
            AACProfile.user_id == current_user.id,
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    await session.delete(profile)
