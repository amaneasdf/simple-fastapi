from tkinter import dnd
import pytest
from sqlalchemy import StaticPool, create_engine, text
from sqlalchemy.orm import sessionmaker
from starlette.routing import _DefaultLifespan
from fastapi.testclient import TestClient

from app.main import app, get_db, create_initial_admin_user
from app.core.database import Base
from app.models import User as UserDB, UserScope as ScopeDB
from app.utils.auth import get_password_hash


# Mock database
engine = create_engine(
    "sqlite:///./test/testdb.db",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


USER_DATA = {
    "username": "admin",
    "email": "admin@localhost.com",
    "fullname": "Administrator",
    "password": get_password_hash("admin"),
    "is_active": True,
    "role": "admin",
    "allowed_scopes": [
        {"scope": "me", "is_active": True},
        {"scope": "admin.assign", "is_active": True},
        {"scope": "users.read", "is_active": True},
        {"scope": "users.write", "is_active": True},
    ],
}


def override_get_db():
    # Override get_db to use TestingSessionLocal
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Fixtures
@pytest.fixture(scope="function")
def mock_user_entry():
    # Setup
    with TestingSessionLocal() as db:
        user = UserDB(
            **{
                **USER_DATA,
                "allowed_scopes": [
                    ScopeDB(**scope) for scope in USER_DATA["allowed_scopes"]
                ],
            }
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Yield user entry
        yield user

        # Teardown
        db.delete(user)
        db.commit()


@pytest.fixture(scope="session", autouse=True)
def client():
    # Setup
    app.dependency_overrides[get_db] = override_get_db

    app.router.lifespan_context = _DefaultLifespan(app.router)

    # Mock startup event
    @app.on_event("startup")
    async def on_startup():
        # Check if table(s) exists in db
        if (
            not TestingSessionLocal()
            .execute(text("SELECT COUNT(*) FROM sqlite_master WHERE type='table'"))
            .scalar()
        ):
            Base.metadata.create_all(engine)

        # Ensure that initial admin user is also created in testing db
        create_initial_admin_user(TestingSessionLocal())

    # Yield client
    with TestClient(app) as client:
        yield client

    # Teardown
    Base.metadata.drop_all(engine)

    app.dependency_overrides.clear()
