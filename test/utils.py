import pytest
from sqlalchemy import StaticPool, create_engine, text
from sqlalchemy.orm import sessionmaker
from starlette.routing import _DefaultLifespan
from fastapi.testclient import TestClient

from app.main import app, get_db, create_initial_admin_user
from app.core.database import Base


# Mock database
engine = create_engine(
    "sqlite:///./testdb.db",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    # Override get_db to use TestingSessionLocal
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


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

        create_initial_admin_user(TestingSessionLocal())

    # Yield client
    with TestClient(app) as client:
        yield client

    # Teardown
    Base.metadata.drop_all(engine)

    app.dependency_overrides.clear()
