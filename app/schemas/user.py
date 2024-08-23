from typing import Optional
from pydantic import BaseModel, Field, EmailStr, field_validator


class BaseSchema(BaseModel):
    id: Optional[int]


class UserBase(BaseModel):
    username: str = Field(min_length=4, max_length=30)
    email: Optional[EmailStr] = None
    fullname: Optional[str] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, value):
        if " " in value:
            raise ValueError("Username cannot contain whitespace")
        return value


class UserCreate(UserBase):
    password: str = Field(min_length=4, max_length=30)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one number")
        if not any(char.isupper() for char in value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in value):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(char in "!@#$%^&*()_+-=[]{}|;:,.<>?/" for char in value):
            raise ValueError("Password must contain at least one special character")
        return value


class UserUpdate(UserBase):
    is_active: bool


class User(BaseSchema, UserBase):
    is_active: bool
    is_superadmin: bool
