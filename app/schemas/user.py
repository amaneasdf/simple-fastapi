from re import match
from typing import Optional, Self
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator


def validate_password(value):
    if not any(char.isdigit() for char in value):
        raise ValueError("Password must contain at least one number")
    if not any(char.isupper() for char in value):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(char.islower() for char in value):
        raise ValueError("Password must contain at least one lowercase letter")
    if not any(char in "!@#$%^&*()_+-=[]{}|;:,.<>?/" for char in value):
        raise ValueError("Password must contain at least one special character")
    return value


class BaseSchema(BaseModel):
    id: Optional[int]


class UserScope(BaseModel):
    scope: str
    is_active: bool


class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    fullname: Optional[str] = None


class UserCreate(UserBase):
    username: str = Field(min_length=6, max_length=30)
    password: str = Field(min_length=8, max_length=30)
    scopes: set[str] = Field(default_factory=set)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value):
        if not value[0].isalpha():
            raise ValueError("Username must start with a letter")
        if not match("^[a-z0-9_-]+$", value):
            raise ValueError(
                "Username can only contain lowercase letters, numbers, dashes and underscores"
            )
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        return validate_password(value)

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, value):
        from ..main import api_scopes

        if value and not all(scope in api_scopes for scope in value):
            raise ValueError("Invalid scope(s)")
        return value


class UserUpdate(UserBase):
    scopes: list[UserScope] = Field(
        default_factory=list, description="List of scopes to add or update"
    )
    remove_scopes: set[str] = Field(
        default_factory=set, description="List of scopes to remove"
    )
    is_active: bool

    @model_validator(mode="after")
    def validate_scopes(self) -> Self:
        from ..main import api_scopes

        if self.scopes and not all(s.scope in api_scopes for s in self.scopes):
            raise ValueError("Invalid scope(s)")

        if self.remove_scopes and not all(s in api_scopes for s in self.remove_scopes):
            raise ValueError("Invalid scope(s)")

        if any(s.scope in self.remove_scopes for s in self.scopes):
            raise ValueError("Cannot remove and add the same scope")

        return self


class UserChangePassword(BaseModel):
    old_password: str
    new_password: str

    @model_validator(mode="after")
    def validate_password(self) -> Self:
        validate_password(self.new_password)

        if self.new_password == self.old_password:
            raise ValueError("New password cannot be the same as the old password")

        return self


class UserRead(BaseSchema, UserBase):
    username: str
    role: str
    is_active: bool


class User(UserRead):
    allowed_scopes: list[UserScope]
