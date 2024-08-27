from fastapi import APIRouter, Depends, HTTPException, status, Security

from ..main import get_current_user
from ..models import User as UserDB
from ..schemas.user import User


router = APIRouter(
    prefix="/user",
    tags=["user"],
    dependencies=[Depends(get_current_user)],
)


@router.get(
    "/me",
    response_model=User,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Not authenticated",
            "content": {
                "application/json": {"example": {"detail": "Not authenticated"}}
            },
        }
    },
)
async def read_users_me(
    current_user: UserDB = Security(get_current_user, scopes=["me"]),
):
    return current_user


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password():
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented"
    )


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password():
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented"
    )
