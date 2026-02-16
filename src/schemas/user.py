from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime, date
from src.models.enums import UserGroupEnum, GenderEnum
import re


# User Registration & Authentication Schemas
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)

    @field_validator('password')
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        """Enforce password complexity requirements"""
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)

    @field_validator('new_password')
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        """Enforce password complexity requirements"""
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

    @field_validator('new_password')
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        """Enforce password complexity requirements"""
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v


# Activation Schemas
class ActivationRequest(BaseModel):
    email: EmailStr


class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar: Optional[str] = None
    gender: Optional[GenderEnum] = None
    date_of_birth: Optional[date] = None
    info: Optional[str] = None


class UserProfileResponse(BaseModel):
    id: int
    user_id: int
    first_name: Optional[str]
    last_name: Optional[str]
    avatar: Optional[str]
    gender: Optional[GenderEnum]
    date_of_birth: Optional[date]
    info: Optional[str]

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    group: str
    profile: Optional[UserProfileResponse] = None

    class Config:
        from_attributes = True


class UserGroupUpdate(BaseModel):
    group: UserGroupEnum


class UserActivate(BaseModel):
    is_active: bool


class Message(BaseModel):
    message: str
