from re import A
from typing import Annotated
from opentelemetry.trace import Tracer
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, status, Security

from ..core.logging import logger
from ..main import get_current_user, get_db
from ..models import AccessToken as AccessTokenDB, User as UserDB
from ..schemas.user import User, UserChangePassword
from ..utils.auth import get_password_hash, verify_password
from ..utils.telemetry import TracerDependency, current_span, get_span_id, get_trace_id


router = APIRouter(
    prefix="/profile",
    tags=["user"],
    dependencies=[Security(get_current_user, scopes=["me"])],
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Not authenticated",
            "content": {
                "application/json": {"example": {"detail": "Not authenticated"}}
            },
        }
    },
)


@router.get("", response_model=User)
async def read_users_me(
    tracer: Annotated[Tracer, Depends(TracerDependency(__name__))],
    current_user: UserDB = Security(get_current_user, scopes=["me"]),
):
    with tracer.start_as_current_span("read_users_me"):
        current_span.set_attribute("user.id", current_user.id)
        logger.info(
            {
                "trace_id": get_trace_id(),
                "span_id": get_span_id(),
                "message": f"Fetching user {current_user.username}",
            }
        )
        return current_user


@router.patch(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "Cannot change password and other user related error (invalid password or other)",
            "content": {
                "application/json": {"example": {"detail": "Cannot change password"}}
            },
        }
    },
)
async def change_password(
    input: UserChangePassword,
    current_user: Annotated[UserDB, Security(get_current_user, scopes=["me"])],
    db: Annotated[Session, Depends(get_db)],
    tracer: Annotated[Tracer, Depends(TracerDependency(__name__))],
):
    with tracer.start_as_current_span("change_password"):
        logger.info(
            {
                "trace_id": get_trace_id(),
                "span_id": get_span_id(),
                "message": f"Changing password for user {current_user.username}",
            }
        )

        # Verify the old password
        if not verify_password(input.old_password, current_user.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change password",
            )

        # Update the password
        with tracer.start_as_current_span("update_password"):
            db.query(UserDB).filter(UserDB.id == current_user.id).update(
                {"password": get_password_hash(input.new_password)}
            )

        # Revoke all the active access tokens of the user
        with tracer.start_as_current_span("revoke_access_tokens"):
            db.query(AccessTokenDB).filter(
                AccessTokenDB.user_id == current_user.id,
                AccessTokenDB.is_revoked == False,
                AccessTokenDB.is_expired == False,
            ).update({AccessTokenDB.is_revoked: True})

        # Commit the transaction
        db.commit()
