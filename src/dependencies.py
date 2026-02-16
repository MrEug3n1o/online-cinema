from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src.database import get_db
from src.models import User, UserGroupEnum
from src.security import decode_access_token
from typing import List

security = HTTPBearer()


def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: int = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensure user is active"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


def require_role(allowed_roles: List[UserGroupEnum]):
    """Create a dependency that checks if user has required role"""

    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.group.name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user

    return role_checker


def get_moderator_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Require moderator or admin role"""
    if current_user.group.name not in [UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator or admin access required"
        )
    return current_user


def get_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Require admin role"""
    if current_user.group.name != UserGroupEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
