from turtle import st
from opentelemetry import trace
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy.orm import Session

from app.core.telemetry import get_span_id, get_trace_id, get_tracer
from app.core.logging import logger
from app.main import get_db
from app.models import User as UserDB, UserScope as UserScopeDB
from app.routes.admin.utils import is_admin
from app.schemas.user import User, UserCreate, UserRead, UserUpdate
from app.utils.auth import get_password_hash


router = APIRouter(prefix="/users")

_tracer = get_tracer(__name__)


def _get_user(db: Session, user_id: int):
    with _tracer.start_as_current_span("fetch_user"):
        user = db.get(UserDB, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return user


def _set_admin_role(db: Session, user_id: int, is_admin: bool):
    with _tracer.start_as_current_span("set_admin_role"):
        trace.get_current_span().set_attributes(
            {"app.input.user_id": user_id, "app.input.is_admin": is_admin}
        )

        # Check if the user exists
        user = db.get(UserDB, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Check if the user is a superadmin
        if user.role == "superadmin" and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges cannot be removed from this user",
            )

        user.role = "admin" if is_admin else "user"
        db.commit()

        logger.info(
            {
                "trace_id": get_trace_id(),
                "span_id": get_span_id(),
                "message": f"User {user_id} role set to {user.role}",
            }
        )


@router.get("/", response_model=list[UserRead])
async def get_all_users(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserDB, Security(is_admin, scopes=["users.read"])],
):
    return db.query(UserDB).all()


@router.post(
    "/",
    response_model=User,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Username already registered"}
    },
)
async def create_user(
    user: UserCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserDB, Security(is_admin, scopes=["users.write"])],
) -> User:
    with _tracer.start_as_current_span("create_user"):
        # Check if the username is already registered
        with _tracer.start_as_current_span("create_user.check_username"):
            trace.get_current_span().set_attribute("app.user.id", current_user.id)
            logger.info(
                {
                    "trace_id": get_trace_id(),
                    "span_id": get_span_id(),
                    "message": f"Creating user {user.username}",
                }
            )
            db_user = db.query(UserDB).filter(UserDB.username == user.username).first()
            if db_user:
                # If the username is already registered, raise an error
                logger.warning(
                    {
                        "trace_id": get_trace_id(),
                        "span_id": get_span_id(),
                        "message": f"User {user.username} already registered",
                    }
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already registered",
                )

        # Create the user
        with _tracer.start_as_current_span("create_user.model_dump"):
            db_user = UserDB(**user.model_dump(exclude={"scopes"}))
            db_user.password = get_password_hash(db_user.password)
            db_user.is_active = True

            # Add scopes to the user
            db_user.allowed_scopes.extend(
                UserScopeDB(scope=scope, is_active=True) for scope in user.scopes
            )
            # Add the "me" scope if it's not already there
            if not any(scope.scope == "me" for scope in db_user.allowed_scopes):
                db_user.allowed_scopes.append(UserScopeDB(scope="me", is_active=True))

        # Save the user to the database
        with _tracer.start_as_current_span("create_user.db_save"):
            db.add(db_user)
            db.commit()
            db.refresh(db_user)

        logger.info(
            {
                "trace_id": get_trace_id(),
                "span_id": get_span_id(),
                "message": f"User {user.username} with id {db_user.id} was created by {current_user.username}",
            }
        )
        return db_user


@router.get(
    "/{user_id}",
    response_model=User,
    responses={status.HTTP_404_NOT_FOUND: {"description": "User not found"}},
)
async def get_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserDB, Security(is_admin, scopes=["users.read"])],
):
    with _tracer.start_as_current_span("get_user"):
        logger.info(f"Fetching user {user_id}")
        return _get_user(db, user_id)


@router.put(
    "/{user_id}",
    response_model=User,
    responses={status.HTTP_404_NOT_FOUND: {"description": "User not found"}},
)
async def update_user(
    user_id: int,
    user: UserUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserDB, Security(is_admin, scopes=["users.update"])],
):
    with _tracer.start_as_current_span("update_user"):
        trace.get_current_span().set_attributes(
            {
                "app.user.id": current_user.id,
                "app.input.user_id": user_id,
            }
        )

        with _tracer.start_as_current_span("update_user.db_get"):
            db_user = _get_user(db, user_id)
            db_user.email = user.email
            db_user.fullname = user.fullname
            db_user.is_active = user.is_active

        if db_user.role != "superadmin":
            with _tracer.start_as_current_span("update_user.compile_scopes"):
                scopes_dict = {s.scope: s for s in db_user.allowed_scopes}
                for scope in user.scopes or []:
                    scopes_dict.setdefault(
                        scope.scope,
                        UserScopeDB(scope=scope.scope, is_active=scope.is_active),
                    ).is_active = scope.is_active
                for scope in user.remove_scopes or []:
                    if scope != "me":  # Cannot remove the "me" scope
                        scopes_dict.pop(scope, None)
                db_user.allowed_scopes = list(scopes_dict.values())

        with _tracer.start_as_current_span("update_user.db_commit"):
            db.commit()
            db.refresh(db_user)
            return db_user


@router.put(
    "/set-admin/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_404_NOT_FOUND: {"description": "User not found"}},
)
async def set_user_as_admin(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: UserDB = Security(is_admin, scopes=["admin.assign"]),
):
    with _tracer.start_as_current_span("set_user_as_admin"):
        trace.get_current_span().set_attributes({"app.user.id": current_user.id})

        # Disallow setting admin privileges for yourself
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot set admin privileges for yourself",
            )

        _set_admin_role(db, user_id, True)


@router.put(
    "/unset-admin/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_404_NOT_FOUND: {"description": "User not found"}},
)
async def unset_user_as_admin(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: UserDB = Security(is_admin, scopes=["admin.assign"]),
):
    with _tracer.start_as_current_span("unset_user_as_admin"):
        trace.get_current_span().set_attributes({"app.user.id": current_user.id})

        # Disallow removing admin privileges from yourself
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot remove admin privileges from yourself by yourself",
            )

        _set_admin_role(db, user_id, False)
