from pydantic import BaseModel
from ulid import ULID


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    id: ULID
    user_id: int
    username: str
    scopes: list[str] = []
