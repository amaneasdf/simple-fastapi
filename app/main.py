from calendar import timegm
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Request, Security, status
from fastapi.security import HTTPBasic, SecurityScopes
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy import func
from sqlalchemy.orm import Session
from ulid import ULID

from .core.config import get_settings
from .core.database import SessionLocal
from .schemas.token import AccessToken, TokenData
from .schemas.user import User
from .models import (
    User as UserDB,
    AccessToken as AccessTokenDB,
)
from .utils.auth import (
    OAuth2ClientCredentials,
    OAuth2ClientCredentialsRequestForm,
    authenticate_user,
    create_access_token,
    decode_access_token,
    get_password_hash,
)

SETTINGS = get_settings()

oauth_scheme = OAuth2ClientCredentials(tokenUrl="/token", scopes={"me": "Me"})


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .models import User

    # Ensure that initial admin user is created
    db = SessionLocal()
    check = db.query(User).where(User.username == SETTINGS.first_admin_username).first()
    if not check:
        print("Creating initial superadmin user...")
        user = User(
            username=SETTINGS.first_admin_username,
            email=None,
            password=get_password_hash(
                SETTINGS.first_admin_password.get_secret_value()
            ),
            fullname="Superadmin",
            is_active=True,
            is_superadmin=True,
        )
        db.add(user)
        db.commit()
    db.close()
    yield


app = FastAPI(
    title=SETTINGS.app_name,
    summary="Simple API using FastAPI. This is me messing around and learning about Python and FastAPI.",
    lifespan=lifespan,
    swagger_ui_parameters={"defaultModelsExpandDepth": -1},
)


# Middleware
@app.middleware("http")
async def add_database_session_middleware(request: Request, call_next):
    try:
        request.state.db = SessionLocal()
        response = await call_next(request)
    finally:
        request.state.db.close()
    return response


def get_db(request: Request):
    return request.state.db


async def get_current_user(
    security_scope: SecurityScopes,
    token: Annotated[str, Depends(oauth_scheme)],
    db: Annotated[Session, Depends(get_db)],
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        tokendata = TokenData(
            id=payload.get("jti"),
            scopes=payload.get("scopes", []),
            username=payload.get("sub"),
        )
    except ExpiredSignatureError:
        credentials_exception.detail = "Token expired"
        raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception

    check_token = (
        db.query(AccessTokenDB)
        .filter(
            AccessTokenDB.token == str(tokendata.id), AccessTokenDB.is_revoked == False
        )
        .first()
    )
    if check_token is None:
        raise credentials_exception

    user = db.query(UserDB).filter(UserDB.username == tokendata.username).first()
    if user is None or not user.is_active or check_token.user_id != user.id:
        credentials_exception.detail = "Invalid credentials"
        raise credentials_exception

    for scope in security_scope.scopes:
        if not any(x.scope == scope for x in user.allowed_scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )

    return user


@app.get("/", include_in_schema=False)
def read_root():
    return {"status": "ok"}


@app.get(
    "/users/me",
    tags=["auth"],
    response_model=User,
    responses={status.HTTP_401_UNAUTHORIZED: {"description": "Not authenticated"}},
)
async def read_users_me(
    # current_user: UserDB = Depends(get_current_user),
    current_user: UserDB = Security(get_current_user, scopes=["me"]),
):
    return current_user


@app.post(
    "/token",
    tags=["auth"],
    response_model=AccessToken,
    responses={status.HTTP_400_BAD_REQUEST: {"description": "Invalid credentials"}},
)
async def get_token(
    form_data: Annotated[OAuth2ClientCredentialsRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
    request: Request,
):
    failed_auth = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Basic"},
    )

    # Check credentials in Basic Auth header too
    basic_creds = await HTTPBasic(auto_error=False)(request)

    # Validate credentials
    if form_data.client_id and form_data.client_secret:
        client_id = form_data.client_id
        client_secret = form_data.client_secret
    elif basic_creds:
        client_id = basic_creds.username
        client_secret = basic_creds.password
    else:
        raise failed_auth
    user = authenticate_user(db, client_id, client_secret)
    if not user:
        raise failed_auth

    # Create access token
    access_token_expires = timedelta(minutes=SETTINGS.access_token_expire_minutes)
    token_id = ULID()
    timestamp = datetime.now(timezone.utc)
    access_token = create_access_token(
        data={"iss": request.client.host, "sub": user.username, "jti": str(token_id)},
        expires_delta=access_token_expires,
    )

    # Store access token info in database
    unixtime = timegm(timestamp.utctimetuple())
    token = AccessTokenDB(
        token=token_id,
        user_id=user.id,
        timestamp=unixtime,
        expired_at=unixtime + access_token_expires.total_seconds(),
    )
    db.add(token)
    db.commit()

    return AccessToken(
        access_token=access_token,
        token_type="bearer",
        expires_in=access_token_expires.total_seconds(),
    )


@app.get("/health")
async def health_check(db: Annotated[Session, Depends(get_db)]):
    from sqlalchemy import select
    from sqlalchemy.exc import OperationalError

    starttime = datetime.now()

    # Check if the database is up
    try:
        dbtest = db.scalar(select(1))
    except OperationalError as e:
        print("Alert:", e)
        dbtest = 0
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal server error")

    totaltime = datetime.now() - starttime

    return {
        "status": "healthy",
        "time": f"{totaltime.total_seconds()} seconds",
        "db": {
            "alias": "localdb",
            "status": "healthy" if dbtest == 1 else "unhealthy",
        },
    }


# Other routes
from .routes import admin

app.router.include_router(admin.router)
