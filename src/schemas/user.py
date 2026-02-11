from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from app.models.user import GenderEnum

class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @validator('password')
    def password_complexity(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        return v

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_active: bool

    class Config:
        orm_mode = True

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
