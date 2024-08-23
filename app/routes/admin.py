from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session


from ..main import get_db, get_current_user
from ..models import User as UserDB
from ..schemas.user import User, UserCreate, UserUpdate
from ..utils.auth import get_password_hash


def is_admin(current_user: Annotated[UserDB, Depends(get_current_user)]):
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return current_user


router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Not authenticated"},
        status.HTTP_403_FORBIDDEN: {"description": "Not enough permissions"},
    },
    dependencies=[Depends(is_admin)],
)


@router.get("/users", response_model=list[User])
async def get_all_users(db: Annotated[Session, Depends(get_db)]):
    return db.query(UserDB).all()


@router.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Annotated[Session, Depends(get_db)]):
    db_user = db.query(UserDB).filter(UserDB.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    db_user = UserDB(**user.model_dump())
    db_user.password = get_password_hash(db_user.password)
    db_user.is_active = True
    db_user.is_superadmin = False
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


@router.get(
    "/users/{user_id}",
    response_model=User,
    responses={status.HTTP_404_NOT_FOUND: {"description": "User not found"}},
)
async def get_user(user_id: int, db: Annotated[Session, Depends(get_db)]):
    user = db.get(UserDB, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return user


@router.put(
    "/users/{user_id}",
    response_model=User,
    responses={status.HTTP_404_NOT_FOUND: {"description": "User not found"}},
)
async def update_user(
    user_id: int, user: UserUpdate, db: Annotated[Session, Depends(get_db)]
):
    db_user = db.get(UserDB, user_id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    db_user.email = user.email
    db_user.fullname = user.fullname
    db_user.is_active = user.is_active
    db.commit()
    db.refresh(db_user)
    return db_user
