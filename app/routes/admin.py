from typing import Annotated, Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy import true
from sqlalchemy.orm import Session


from ..main import get_db, get_current_user
from ..models import User as UserDB, UserScope as UserScopeDB
from ..schemas.user import User, UserCreate, UserRead, UserUpdate
from ..utils.auth import get_password_hash


def is_admin(current_user: Annotated[UserDB, Depends(get_current_user)]):
    noperm_exc = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
    )
    if not current_user.is_superadmin:
        raise noperm_exc
    return current_user


def _get_user(db: Session, user_id: int):
    user = db.get(UserDB, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Not authenticated"},
        status.HTTP_403_FORBIDDEN: {"description": "Not enough permissions"},
    },
    dependencies=[Depends(is_admin)],
)


@router.get("/scopes", response_model=dict[str, str])
async def get_scopes():
    from ..main import api_scopes

    return api_scopes


@router.get("/users", response_model=list[UserRead])
async def get_all_users(db: Annotated[Session, Depends(get_db)]):
    return db.query(UserDB).all()


@router.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate, db: Annotated[Session, Depends(get_db)]
) -> User:
    # Check if the username is already registered
    db_user = db.query(UserDB).filter(UserDB.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Create the user
    db_user = UserDB(**user.model_dump(exclude={"scopes"}))
    db_user.password = get_password_hash(db_user.password)
    db_user.is_active = True
    db_user.is_superadmin = False

    # Add scopes to the user
    db_user.allowed_scopes.extend(
        UserScopeDB(scope=scope, is_active=True)
        for scope in user.scopes
        if scope != "admin.assign"
    )
    # Add the "me" scope if it's not already there
    if not any(scope.scope == "me" for scope in db_user.allowed_scopes):
        db_user.allowed_scopes.append(UserScopeDB(scope="me", is_active=True))

    # Save the user to the database
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
    return _get_user(db, user_id)


@router.put(
    "/users/{user_id}",
    response_model=User,
    responses={status.HTTP_404_NOT_FOUND: {"description": "User not found"}},
)
async def update_user(
    user_id: int, user: UserUpdate, db: Annotated[Session, Depends(get_db)]
):
    db_user = _get_user(db, user_id)
    db_user.email = user.email
    db_user.fullname = user.fullname
    db_user.is_active = user.is_active

    # Update user's scopes
    scopes_dict = {s.scope: s for s in db_user.allowed_scopes}
    if user.scopes:
        # Add or update scopes
        for scope in user.scopes:
            if scope.scope in [
                "admin",
                "admin.assign",
            ]:  # Cannot add admin related scopes
                continue
            if scope.scope in scopes_dict:
                scopes_dict[scope.scope].is_active = scope.is_active
            else:
                scopes_dict[scope.scope] = UserScopeDB(
                    scope=scope.scope, is_active=scope.is_active
                )
    if user.remove_scopes:
        # Remove scopes
        for scope in user.remove_scopes:
            if scope in ["me", "admin"]:  # Cannot remove the "me" or "admin" scopes
                continue
            if scope in scopes_dict.keys():
                scopes_dict.pop(scope)
    db_user.allowed_scopes = list(scopes_dict.values())

    db.commit()
    db.refresh(db_user)
    return db_user


@router.put("/users/{user_id}/set-admin", status_code=status.HTTP_204_NO_CONTENT)
async def set_user_as_admin(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: UserDB = Security(is_admin, scopes=["admin.assign"]),
    super: Optional[Literal[1, 0]] = None,
):
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot set admin privileges for yourself",
        )
    db_user = _get_user(db, user_id)
    if super == 1:
        db_user.is_superadmin = True
        db_user.allowed_scopes.append(UserScopeDB(scope="admin.assign", is_active=True))
    else:
        db_user.allowed_scopes.append(UserScopeDB(scope="admin", is_active=True))
    db.commit()


@router.put("/users/{user_id}/unset-admin", status_code=status.HTTP_204_NO_CONTENT)
async def unset_user_as_admin(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: UserDB = Security(is_admin, scopes=["admin.assign"]),
):
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot remove admin privileges from yourself by yourself",
        )
    db_user = _get_user(db, user_id)
    db_user.is_superadmin = False
    db_user.allowed_scopes = [
        scope
        for scope in db_user.allowed_scopes
        if scope.scope not in ["admin", "admin.assign"]
    ]
    db.commit()
