from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import get_settings


_settings = get_settings()

SQLALCHEMY_DATABASE_URL = _settings.database_url
# SQLALCHEMY_DATABASE_URL = "postgresql://user:password@postgresserver/db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

if _settings.telemetry.enabled and _settings.telemetry.trace_sqlalchemy:
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from .telemetry import provider

    SQLAlchemyInstrumentor().instrument(
        engine=engine, tracer_provider=provider, enable_commenter=True
    )
