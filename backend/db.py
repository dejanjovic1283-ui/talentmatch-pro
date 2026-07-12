from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


load_dotenv()


def normalize_database_url(raw_url: str) -> str:
    """
    Normalize Render/PostgreSQL URLs for SQLAlchemy and psycopg 3.

    Render provides URLs that usually start with ``postgresql://``.
    SQLAlchemy interprets that scheme as the legacy psycopg2 driver unless
    an explicit driver is provided. TalentMatch Pro uses psycopg 3 through
    ``psycopg[binary]``, so PostgreSQL URLs are converted to
    ``postgresql+psycopg://``.
    """
    database_url = raw_url.strip()

    if database_url.startswith("postgres://"):
        return "postgresql+psycopg://" + database_url[len("postgres://") :]

    if database_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + database_url[len("postgresql://") :]

    return database_url


RAW_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./talentmatch.db",
).strip()

DATABASE_URL = normalize_database_url(RAW_DATABASE_URL)

IS_SQLITE = DATABASE_URL.startswith("sqlite")
IS_POSTGRESQL = DATABASE_URL.startswith("postgresql+psycopg://")

connect_args: dict[str, object] = {}

if IS_SQLITE:
    connect_args["check_same_thread"] = False

engine_options: dict[str, object] = {
    "connect_args": connect_args,
    "pool_pre_ping": True,
}

if IS_SQLITE:
    engine_options["pool_recycle"] = -1
else:
    engine_options.update(
        {
            "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT_SECONDS", "30")),
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE_SECONDS", "300")),
        }
    )

engine: Engine = create_engine(
    DATABASE_URL,
    **engine_options,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


def get_db():
    """Yield a request-scoped SQLAlchemy database session."""
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
