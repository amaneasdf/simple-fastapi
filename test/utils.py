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
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db

    app.router.lifespan_context = _DefaultLifespan(app.router)

    # Mock startup event
    @app.on_event("startup")
    async def on_startup():
        db = TestingSessionLocal()
        # Check if table(s) exists in db
        if db.execute(text("SELECT COUNT(*) FROM sqlite_master")).scalar() == 0:
            Base.metadata.create_all(db.bind)

        create_initial_admin_user(db)
        db.close()

    with TestClient(app) as client:
        yield client
