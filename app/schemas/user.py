from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    fullname: Optional[str] = None


class UserCreate(UserBase):
    username: str = Field(min_length=4, max_length=30)
    password: str = Field(min_length=4, max_length=30)


class UserUpdate(UserBase):
    email: Optional[EmailStr] = None
    is_active: bool


class User(UserBase):
    id: int
    username: str
    is_active: bool
    is_superadmin: bool
