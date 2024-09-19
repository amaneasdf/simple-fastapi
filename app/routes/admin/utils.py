from typing import Annotated
from fastapi import Depends, HTTPException, status

from app.main import get_current_user
from app.models import User as UserDB


def is_admin(current_user: Annotated[UserDB, Depends(get_current_user)]):
    noperm_exc = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
    )
    if current_user.role not in ("admin", "superadmin"):
        raise noperm_exc
    return current_user
