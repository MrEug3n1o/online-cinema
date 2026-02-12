from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from src.database import get_db
from src.models import User, UserGroup, UserProfile, ActivationToken, PasswordResetToken, RefreshToken
from src.models.enums import UserGroupEnum
from src.schemas.user import (
    UserRegister,
    UserLogin,
    Token,
    TokenRefresh,
    AccessToken,
    PasswordChange,
    PasswordResetRequest,
    PasswordReset,
    ActivationRequest,
    Message,
)
from src.security import (
    verify_password, get_password_hash, create_access_token,
    create_refresh_token, generate_token
)
from src.email import send_activation_email, send_password_reset_email
from src.dependencies import get_current_active_user
from src.config import get_settings

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


@router.post("/register", response_model=Message, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user and send activation email"""
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    user_group = db.query(UserGroup).filter(UserGroup.name == UserGroupEnum.USER).first()
    if not user_group:
        user_group = UserGroup(name=UserGroupEnum.USER)
        db.add(user_group)
        db.commit()
        db.refresh(user_group)

    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        is_active=False,
        group_id=user_group.id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    profile = UserProfile(user_id=new_user.id)
    db.add(profile)

    token = generate_token()
    expires_at = datetime.utcnow() + timedelta(hours=settings.ACTIVATION_TOKEN_EXPIRE_HOURS)
    activation_token = ActivationToken(
        user_id=new_user.id,
        token=token,
        expires_at=expires_at
    )
    db.add(activation_token)
    db.commit()

    send_activation_email(new_user.email, token)

    return {"message": "Registration successful. Please check your email to activate your account."}


@router.post("/activate", response_model=Message)
def activate_account(token: str, db: Session = Depends(get_db)):
    """Activate user account with token"""
    activation_token = db.query(ActivationToken).filter(
        ActivationToken.token == token
    ).first()

    if not activation_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid activation token"
        )

    if activation_token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Activation token expired"
        )

    user = activation_token.user
    user.is_active = True
    db.delete(activation_token)
    db.commit()

    return {"message": "Account activated successfully"}


@router.post("/resend-activation", response_model=Message)
def resend_activation(request: ActivationRequest, db: Session = Depends(get_db)):
    """Resend activation email if token expired"""
    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account already activated"
        )

    old_token = db.query(ActivationToken).filter(
        ActivationToken.user_id == user.id
    ).first()
    if old_token:
        db.delete(old_token)

    token = generate_token()
    expires_at = datetime.utcnow() + timedelta(hours=settings.ACTIVATION_TOKEN_EXPIRE_HOURS)
    activation_token = ActivationToken(
        user_id=user.id,
        token=token,
        expires_at=expires_at
    )
    db.add(activation_token)
    db.commit()

    send_activation_email(user.email, token)

    return {"message": "Activation email sent successfully"}


@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login and receive JWT tokens"""
    user = db.query(User).filter(User.email == user_data.email).first()

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not activated. Please check your email."
        )

    access_token = create_access_token(data={"sub": user.id})

    refresh_token_str = create_refresh_token()
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_str,
        expires_at=expires_at
    )
    db.add(refresh_token)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token_str,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=AccessToken)
def refresh_token(token_data: TokenRefresh, db: Session = Depends(get_db)):
    """Get new access token using refresh token"""
    refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token == token_data.refresh_token
    ).first()

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    if refresh_token.expires_at < datetime.utcnow():
        db.delete(refresh_token)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired"
        )

    user = refresh_token.user
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not active"
        )

    access_token = create_access_token(data={"sub": user.id})

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/logout", response_model=Message)
def logout(
        token_data: TokenRefresh,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Logout by deleting refresh token"""
    refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token == token_data.refresh_token,
        RefreshToken.user_id == current_user.id
    ).first()

    if refresh_token:
        db.delete(refresh_token)
        db.commit()

    return {"message": "Logged out successfully"}


@router.post("/change-password", response_model=Message)
def change_password(
        password_data: PasswordChange,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Change password when user knows old password"""
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password"
        )

    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()

    return {"message": "Password changed successfully"}


@router.post("/forgot-password", response_model=Message)
def forgot_password(request: PasswordResetRequest, db: Session = Depends(get_db)):
    """Request password reset email"""
    user = db.query(User).filter(User.email == request.email).first()

    if not user or not user.is_active:
        return {"message": "If the email is registered and active, a password reset link has been sent."}

    old_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id
    ).first()
    if old_token:
        db.delete(old_token)

    token = generate_token()
    expires_at = datetime.utcnow() + timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=expires_at
    )
    db.add(reset_token)
    db.commit()

    send_password_reset_email(user.email, token)

    return {"message": "If the email is registered and active, a password reset link has been sent."}


@router.post("/reset-password", response_model=Message)
def reset_password(reset_data: PasswordReset, db: Session = Depends(get_db)):
    """Reset password with token"""
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == reset_data.token
    ).first()

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token"
        )

    if reset_token.expires_at < datetime.utcnow():
        db.delete(reset_token)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token expired"
        )

    user = reset_token.user
    user.hashed_password = get_password_hash(reset_data.new_password)
    db.delete(reset_token)
    db.commit()

    return {"message": "Password reset successfully"}
