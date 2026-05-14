from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.role import RoleRead


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=64)
    full_name: str | None = Field(default=None, max_length=128)
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)
    role_id: int


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, max_length=128)
    is_active: bool | None = None
    role_id: int | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: RoleRead
    created_at: datetime
    updated_at: datetime


class UserBrief(BaseModel):
    """Lightweight user payload for selectors (e.g. salesperson picker)."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    full_name: str | None
    role_name: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str
