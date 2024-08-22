from calendar import timegm
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPBasic
from sqlalchemy.orm import Session
from ulid import ULID

from .core.config import get_settings
from .core.database import SessionLocal
from .schemas.token import AccessToken
from .utils.auth import (
    OAuth2ClientCredentials,
    OAuth2ClientCredentialsRequestForm,
    authenticate_user,
    create_access_token,
    get_password_hash,
    decode_access_token,
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


async def get_current_user(token: Annotated[str, Depends(oauth_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    return


@app.get("/", include_in_schema=False)
def read_root():
    return {"Hello": "World"}


@app.post("/token", tags=["auth"], response_model=AccessToken)
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
    from .models import AccessToken as AccessTokenModel

    unixtime = timegm(timestamp.utctimetuple())
    token = AccessTokenModel(
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

    # Check if the database is up
    try:
        dbtest = db.scalar(select(1))
    except OperationalError as e:
        print("Alert:", e)
        dbtest = 0
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"status": "ok", "db": dbtest == 1}
