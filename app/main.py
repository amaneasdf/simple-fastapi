from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .core.config import get_settings
from .core.database import SessionLocal
from .utils.auth import get_password_hash

SETTINGS = get_settings()

oauth_scheme = OAuth2PasswordBearer(tokenUrl="/token")


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
            email="",
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


@app.get("/")
def read_root():
    return {"Hello": "World"}


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
