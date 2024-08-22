from pydantic import BaseModel


class User(BaseModel):
    id: int
    username: str
    email: str | None = None
    fullname: str | None = None
    is_active: bool = True
    is_superadmin: bool = False


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    user: User
    scopes: list[str] = []
