from fastapi import APIRouter, Depends, status

from app.routes.admin import users
from .utils import is_admin

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Not authenticated"},
        status.HTTP_403_FORBIDDEN: {"description": "Not enough permissions"},
    },
)


router.include_router(users.router)
