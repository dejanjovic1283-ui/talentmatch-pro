from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from typing import Generator, Iterator

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import (
    DBAPIError,
    IntegrityError,
    OperationalError,
    SQLAlchemyError,
    TimeoutError as SQLAlchemyTimeoutError,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import Pool


load_dotenv()

logger = logging.getLogger("talentmatch.database")


def _get_int_env(
    name: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    raw_value = os.getenv(name, str(default)).strip()

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(
            f"{name} must be an integer between {minimum} and {maximum}."
        ) from exc

    if value < minimum or value > maximum:
        raise RuntimeError(
            f"{name} must be between {minimum} and {maximum}."
        )

    return value


def _get_bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()

    if normalized in {"1", "true", "yes", "on"}:
        return True

    if normalized in {"0", "false", "no", "off"}:
        return False

    raise RuntimeError(
        f"{name} must be one of: true, false, 1, 0, yes, no, on, off."
    )


def normalize_database_url(raw_url: str) -> str:
    """
    Normalize PostgreSQL URLs for SQLAlchemy and psycopg 3.

    Render commonly provides ``postgresql://`` URLs. SQLAlchemy interprets
    that scheme as the legacy psycopg2 driver unless a driver is explicit.
    TalentMatch Pro uses psycopg 3, therefore PostgreSQL URLs are normalized
    to ``postgresql+psycopg://``.
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

DB_POOL_SIZE = _get_int_env(
    "DB_POOL_SIZE",
    5,
    minimum=1,
    maximum=50,
)
DB_MAX_OVERFLOW = _get_int_env(
    "DB_MAX_OVERFLOW",
    10,
    minimum=0,
    maximum=100,
)
DB_POOL_TIMEOUT_SECONDS = _get_int_env(
    "DB_POOL_TIMEOUT_SECONDS",
    30,
    minimum=1,
    maximum=300,
)
DB_POOL_RECYCLE_SECONDS = _get_int_env(
    "DB_POOL_RECYCLE_SECONDS",
    300,
    minimum=30,
    maximum=86_400,
)
DB_CONNECT_TIMEOUT_SECONDS = _get_int_env(
    "DB_CONNECT_TIMEOUT_SECONDS",
    10,
    minimum=1,
    maximum=120,
)
DB_STATEMENT_TIMEOUT_MS = _get_int_env(
    "DB_STATEMENT_TIMEOUT_MS",
    30_000,
    minimum=1_000,
    maximum=300_000,
)
DB_ECHO = _get_bool_env("DB_ECHO", False)


def _build_connect_args() -> dict[str, object]:
    if IS_SQLITE:
        return {
            "check_same_thread": False,
        }

    if IS_POSTGRESQL:
        return {
            "connect_timeout": DB_CONNECT_TIMEOUT_SECONDS,
            "application_name": "talentmatch-pro",
            "options": f"-c statement_timeout={DB_STATEMENT_TIMEOUT_MS}",
        }

    return {}


def _build_engine_options() -> dict[str, object]:
    options: dict[str, object] = {
        "connect_args": _build_connect_args(),
        "pool_pre_ping": True,
        "echo": DB_ECHO,
        "future": True,
    }

    if IS_SQLITE:
        options["pool_recycle"] = -1
    else:
        options.update(
            {
                "pool_size": DB_POOL_SIZE,
                "max_overflow": DB_MAX_OVERFLOW,
                "pool_timeout": DB_POOL_TIMEOUT_SECONDS,
                "pool_recycle": DB_POOL_RECYCLE_SECONDS,
            }
        )

    return options


engine: Engine = create_engine(
    DATABASE_URL,
    **_build_engine_options(),
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
    class_=Session,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


@dataclass(frozen=True)
class DatabaseConnectionStatus:
    ok: bool
    dialect: str
    driver: str
    error_type: str | None = None
    retryable: bool | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DatabaseErrorInfo:
    error_type: str
    message: str
    status_code: int
    retryable: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def get_db() -> Generator[Session, None, None]:
    """
    Yield a request-scoped SQLAlchemy session.

    Any unhandled exception causes an explicit rollback before the session is
    closed. Commits remain explicit in service/route code so read-only requests
    never commit implicitly.
    """
    db = SessionLocal()

    try:
        yield db
    except BaseException:
        if db.in_transaction():
            db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def database_session() -> Iterator[Session]:
    """
    Context manager for non-request database work.

    Successful operations are committed. Any exception triggers rollback and
    is re-raised. The session is always closed.
    """
    db = SessionLocal()

    try:
        yield db
        db.commit()
    except BaseException:
        if db.in_transaction():
            db.rollback()
        raise
    finally:
        db.close()


def rollback_session_safely(db: Session) -> None:
    """Rollback a failed transaction without masking the original exception."""
    try:
        if db.in_transaction():
            db.rollback()
    except SQLAlchemyError:
        logger.exception(
            "Database rollback failed.",
            extra={
                "event": "database_rollback_failed",
            },
        )


def check_database_connection() -> DatabaseConnectionStatus:
    """
    Execute a lightweight readiness query.

    The result intentionally contains no hostname, username, password, query
    payload, or connection URL.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return DatabaseConnectionStatus(
            ok=True,
            dialect=engine.dialect.name,
            driver=engine.dialect.driver,
        )
    except SQLAlchemyTimeoutError:
        return DatabaseConnectionStatus(
            ok=False,
            dialect=engine.dialect.name,
            driver=engine.dialect.driver,
            error_type="database_timeout",
            retryable=True,
        )
    except OperationalError:
        return DatabaseConnectionStatus(
            ok=False,
            dialect=engine.dialect.name,
            driver=engine.dialect.driver,
            error_type="database_unavailable",
            retryable=True,
        )
    except SQLAlchemyError:
        return DatabaseConnectionStatus(
            ok=False,
            dialect=engine.dialect.name,
            driver=engine.dialect.driver,
            error_type="database_error",
            retryable=False,
        )


def _safe_pool_metric(pool: Pool, method_name: str) -> int | None:
    method = getattr(pool, method_name, None)

    if not callable(method):
        return None

    try:
        value = method()
    except (TypeError, NotImplementedError):
        return None

    return int(value) if isinstance(value, int) else None


def get_database_pool_status() -> dict[str, object]:
    """
    Return safe SQLAlchemy pool metrics.

    No database credentials or network location details are exposed.
    """
    pool = engine.pool

    return {
        "enabled": not IS_SQLITE,
        "pool_type": type(pool).__name__,
        "pool_size": _safe_pool_metric(pool, "size"),
        "checked_in": _safe_pool_metric(pool, "checkedin"),
        "checked_out": _safe_pool_metric(pool, "checkedout"),
        "overflow": _safe_pool_metric(pool, "overflow"),
        "timeout_seconds": (
            DB_POOL_TIMEOUT_SECONDS if not IS_SQLITE else None
        ),
        "recycle_seconds": (
            DB_POOL_RECYCLE_SECONDS if not IS_SQLITE else None
        ),
    }


def get_database_reliability_status() -> dict[str, object]:
    connection_status = check_database_connection()
    pool_status = get_database_pool_status()

    return {
        "connection_ok": connection_status.ok,
        "dialect": connection_status.dialect,
        "driver": connection_status.driver,
        "error_type": connection_status.error_type,
        "retryable": connection_status.retryable,
        "pool_enabled": pool_status["enabled"],
        "transaction_safety_enabled": True,
        "timeout_protection_enabled": True,
        "connect_timeout_seconds": (
            DB_CONNECT_TIMEOUT_SECONDS if IS_POSTGRESQL else None
        ),
        "statement_timeout_ms": (
            DB_STATEMENT_TIMEOUT_MS if IS_POSTGRESQL else None
        ),
        "pool": pool_status,
    }


def dispose_engine() -> None:
    """Close all pooled database connections."""
    engine.dispose()


def classify_database_exception(exc: BaseException) -> DatabaseErrorInfo:
    """
    Convert SQLAlchemy exceptions into a stable public error classification.

    Returned messages are intentionally generic and never contain SQL text,
    table names, credentials, hostnames, or user-provided payloads.
    """
    if isinstance(exc, IntegrityError):
        return DatabaseErrorInfo(
            error_type="database_conflict",
            message="The database operation conflicts with existing data.",
            status_code=409,
            retryable=False,
        )

    if isinstance(exc, SQLAlchemyTimeoutError):
        return DatabaseErrorInfo(
            error_type="database_timeout",
            message="The database did not respond within the allowed time.",
            status_code=504,
            retryable=True,
        )

    if isinstance(exc, OperationalError):
        return DatabaseErrorInfo(
            error_type="database_unavailable",
            message="The database is temporarily unavailable.",
            status_code=503,
            retryable=True,
        )

    if isinstance(exc, DBAPIError) and exc.connection_invalidated:
        return DatabaseErrorInfo(
            error_type="database_connection_lost",
            message="The database connection was interrupted.",
            status_code=503,
            retryable=True,
        )

    if isinstance(exc, SQLAlchemyError):
        return DatabaseErrorInfo(
            error_type="database_error",
            message="A database operation could not be completed.",
            status_code=500,
            retryable=False,
        )

    return DatabaseErrorInfo(
        error_type="database_error",
        message="An unexpected database error occurred.",
        status_code=500,
        retryable=False,
    )
