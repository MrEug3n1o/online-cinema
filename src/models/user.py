from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Enum, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from src.database import Base


class UserGroupEnum(str, enum.Enum):
    USER = "USER"
    MODERATOR = "MODERATOR"
    ADMIN = "ADMIN"


class GenderEnum(str, enum.Enum):
    MAN = "MAN"
    WOMAN = "WOMAN"


class UserGroup(Base):
    __tablename__ = "user_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, default=UserGroupEnum.USER)

    users = relationship("User", back_populates="group")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    group_id = Column(Integer, ForeignKey("user_groups.id"))

    group = relationship("UserGroup", back_populates="users")
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    activation_token = relationship("ActivationToken", back_populates="user", uselist=False)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    avatar = Column(String, nullable=True)  # S3 URL
    gender = Column(Enum(GenderEnum), nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    info = Column(String, nullable=True)

    user = relationship("User", back_populates="profile")