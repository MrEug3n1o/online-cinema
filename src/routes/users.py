from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.models import User, UserProfile
from src.schemas.user import UserResponse, UserProfileUpdate, UserProfileResponse
from src.dependencies import get_current_active_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
        "group": current_user.group.name.value,
        "profile": current_user.profile
    }


@router.get("/me/profile", response_model=UserProfileResponse)
def get_user_profile(
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Get current user profile"""
    profile = current_user.profile
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return profile


@router.put("/me/profile", response_model=UserProfileResponse)
def update_user_profile(
        profile_data: UserProfileUpdate,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Update current user profile"""
    profile = current_user.profile
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    update_data = profile_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)

    return profile