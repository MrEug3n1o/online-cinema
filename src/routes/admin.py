from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from src.database import get_db
from src.models.user import User, UserGroup
from src.models.enums import UserGroupEnum
from src.schemas.user import UserResponse, UserGroupUpdate, UserActivate, Message
from src.dependencies import get_admin_user

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=List[UserResponse])
def get_all_users(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_admin_user)
):
    """Get all users (admin only)"""
    users = db.query(User).offset(skip).limit(limit).all()

    return [
        {
            "id": user.id,
            "email": user.email,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "group": user.group.name.value,
            "profile": user.profile
        }
        for user in users
    ]


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user_by_id(
        user_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_admin_user)
):
    """Get user by ID (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {
        "id": user.id,
        "email": user.email,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "group": user.group.name.value,
        "profile": user.profile
    }


@router.patch("/users/{user_id}/group", response_model=UserResponse)
def update_user_group(
        user_id: int,
        group_data: UserGroupUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_admin_user)
):
    """Update user group (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    new_group = db.query(UserGroup).filter(
        UserGroup.name == group_data.group
    ).first()

    if not new_group:
        new_group = UserGroup(name=group_data.group)
        db.add(new_group)
        db.commit()
        db.refresh(new_group)

    user.group_id = new_group.id
    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "group": user.group.name.value,
        "profile": user.profile
    }


@router.patch("/users/{user_id}/activate", response_model=UserResponse)
def activate_user_manually(
        user_id: int,
        activation_data: UserActivate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_admin_user)
):
    """Manually activate/deactivate user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.is_active = activation_data.is_active
    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "group": user.group.name.value,
        "profile": user.profile
    }


@router.delete("/users/{user_id}", response_model=Message)
def delete_user(
        user_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_admin_user)
):
    """Delete user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    db.delete(user)
    db.commit()

    return {"message": "User deleted successfully"}
