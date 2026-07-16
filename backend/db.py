from __future__ import annotations

import logging
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from typing import Callable, Final, Generator, Iterator, TypeAlias, TypeVar

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
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


# ---------------------------------------------------------------------------
# Types and constants
# ---------------------------------------------------------------------------

ConnectArgs: TypeAlias = dict[str, object]
EngineOptions: TypeAlias = dict[str, object]
DatabaseStatusPayload: TypeAlias = dict[str, object]

T = TypeVar("T")

APPLICATION_NAME: Final[str] = "talentmatch-pro"
DEFAULT_DATABASE_URL: Final[str] = "sqlite:///./talentmatch.db"

TRANSIENT_RETRY_ATTEMPTS: Final[int] = 2
TRANSIENT_RETRY_DELAY_SECONDS: Final[float] = 0.25

_TRUE_VALUES: Final[frozenset[str]] = frozenset(
    {"1", "true", "yes", "on"}
)
_FALSE_VALUES: Final[frozenset[str]] = frozenset(
    {"0", "false", "no", "off"}
)

_active_sessions = 0
_active_sessions_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Environment parsing
# ---------------------------------------------------------------------------

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

    if normalized in _TRUE_VALUES:
        return True

    if normalized in _FALSE_VALUES:
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
    DEFAULT_DATABASE_URL,
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


# ---------------------------------------------------------------------------
# Engine configuration
# ---------------------------------------------------------------------------

def _build_connect_args() -> ConnectArgs:
    if IS_SQLITE:
        return {
            "check_same_thread": False,
        }

    if IS_POSTGRESQL:
        return {
            "connect_timeout": DB_CONNECT_TIMEOUT_SECONDS,
            "application_name": APPLICATION_NAME,
            "options": f"-c statement_timeout={DB_STATEMENT_TIMEOUT_MS}",
        }

    return {}


def _build_engine_options() -> EngineOptions:
    options: EngineOptions = {
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


def validate_engine_configuration() -> None:
    """
    Validate the active database engine configuration before initialization.

    Validation intentionally avoids logging or exposing the connection URL.
    """
    if not IS_SQLITE and not IS_POSTGRESQL:
        raise RuntimeError(
            "DATABASE_URL must use SQLite or PostgreSQL with psycopg 3."
        )

    if IS_POSTGRESQL and "+psycopg" not in DATABASE_URL:
        raise RuntimeError(
            "PostgreSQL connections must use the psycopg 3 driver."
        )

    effective_capacity = DB_POOL_SIZE + DB_MAX_OVERFLOW
    if effective_capacity > 150:
        raise RuntimeError(
            "The configured database pool capacity is too large."
        )


validate_engine_configuration()

ENGINE_OPTIONS: Final[EngineOptions] = _build_engine_options()

engine: Engine = create_engine(
    DATABASE_URL,
    **ENGINE_OPTIONS,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
    class_=Session,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""


# ---------------------------------------------------------------------------
# Structured result models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DatabaseConnectionStatus:
    """Safe database readiness result."""

    ok: bool
    dialect: str
    driver: str
    error_type: str | None = None
    retryable: bool | None = None

    def to_dict(self) -> DatabaseStatusPayload:
        return asdict(self)


@dataclass(frozen=True)
class DatabaseErrorInfo:
    """Stable public classification of a database exception."""

    error_type: str
    message: str
    status_code: int
    retryable: bool

    def to_dict(self) -> DatabaseStatusPayload:
        return asdict(self)


# ---------------------------------------------------------------------------
# Session tracking
# ---------------------------------------------------------------------------

def _increment_active_sessions() -> None:
    global _active_sessions

    with _active_sessions_lock:
        _active_sessions += 1


def _decrement_active_sessions() -> None:
    global _active_sessions

    with _active_sessions_lock:
        _active_sessions = max(0, _active_sessions - 1)


def get_active_session_count() -> int:
    """Return the number of currently open application sessions."""
    with _active_sessions_lock:
        return _active_sessions


# ---------------------------------------------------------------------------
# Pool lifecycle telemetry
# ---------------------------------------------------------------------------

def _register_pool_event_logging(database_engine: Engine) -> None:
    """
    Register non-sensitive pool lifecycle telemetry.

    No SQL, hostnames, credentials, database names or user payloads are logged.
    """

    @event.listens_for(database_engine, "connect")
    def _on_connect(
        _dbapi_connection: object,
        _connection_record: object,
    ) -> None:
        logger.debug(
            "Database connection created.",
            extra={"event": "database_connection_created"},
        )

    @event.listens_for(database_engine, "checkout")
    def _on_checkout(
        _dbapi_connection: object,
        _connection_record: object,
        _connection_proxy: object,
    ) -> None:
        logger.debug(
            "Database connection checked out.",
            extra={"event": "database_connection_checked_out"},
        )

    @event.listens_for(database_engine, "checkin")
    def _on_checkin(
        _dbapi_connection: object,
        _connection_record: object,
    ) -> None:
        logger.debug(
            "Database connection checked in.",
            extra={"event": "database_connection_checked_in"},
        )

    @event.listens_for(database_engine, "invalidate")
    def _on_invalidate(
        _dbapi_connection: object,
        _connection_record: object,
        exception: BaseException | None,
    ) -> None:
        logger.warning(
            "Database connection invalidated.",
            extra={
                "event": "database_connection_invalidated",
                "error_type": (
                    type(exception).__name__ if exception else None
                ),
            },
        )


_register_pool_event_logging(engine)


def log_database_startup_summary() -> None:
    """Log safe, non-secret database runtime configuration."""
    logger.info(
        "Database engine initialized.",
        extra={
            "event": "database_engine_initialized",
            "dialect": engine.dialect.name,
            "driver": engine.dialect.driver,
            "pool_enabled": not IS_SQLITE,
            "pool_type": type(engine.pool).__name__,
            "pool_size": DB_POOL_SIZE if not IS_SQLITE else None,
            "max_overflow": DB_MAX_OVERFLOW if not IS_SQLITE else None,
            "pool_timeout_seconds": (
                DB_POOL_TIMEOUT_SECONDS if not IS_SQLITE else None
            ),
            "pool_recycle_seconds": (
                DB_POOL_RECYCLE_SECONDS if not IS_SQLITE else None
            ),
            "connect_timeout_seconds": (
                DB_CONNECT_TIMEOUT_SECONDS if IS_POSTGRESQL else None
            ),
            "statement_timeout_ms": (
                DB_STATEMENT_TIMEOUT_MS if IS_POSTGRESQL else None
            ),
        },
    )


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

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


def get_db() -> Generator[Session, None, None]:
    """
    Yield a request-scoped SQLAlchemy session.

    Unhandled exceptions trigger rollback before close. Commits remain explicit
    in route and service code so read-only requests never commit implicitly.
    """
    db = SessionLocal()
    _increment_active_sessions()

    try:
        yield db
    except BaseException:
        rollback_session_safely(db)
        raise
    finally:
        try:
            db.close()
        finally:
            _decrement_active_sessions()


@contextmanager
def database_session() -> Iterator[Session]:
    """
    Context manager for non-request database work.

    Successful operations commit. Exceptions trigger rollback and are re-raised.
    The session is always closed and active-session telemetry remains accurate.
    """
    db = SessionLocal()
    _increment_active_sessions()

    try:
        yield db
        db.commit()
    except BaseException:
        rollback_session_safely(db)
        raise
    finally:
        try:
            db.close()
        finally:
            _decrement_active_sessions()


# ---------------------------------------------------------------------------
# Error classification and bounded retry
# ---------------------------------------------------------------------------

def classify_database_exception(exc: BaseException) -> DatabaseErrorInfo:
    """
    Convert SQLAlchemy exceptions into a stable public classification.

    Returned messages never contain SQL text, table names, credentials,
    hostnames or user-provided payloads.
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

    if isinstance(exc, DBAPIError) and exc.connection_invalidated:
        return DatabaseErrorInfo(
            error_type="database_connection_lost",
            message="The database connection was interrupted.",
            status_code=503,
            retryable=True,
        )

    if isinstance(exc, OperationalError):
        return DatabaseErrorInfo(
            error_type="database_unavailable",
            message="The database is temporarily unavailable.",
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


def execute_with_retry(
    operation: Callable[[], T],
    *,
    attempts: int = TRANSIENT_RETRY_ATTEMPTS,
    delay_seconds: float = TRANSIENT_RETRY_DELAY_SECONDS,
) -> T:
    """
    Execute an idempotent database operation with bounded retries.

    Use this helper only for read operations or explicitly idempotent writes.
    Integrity conflicts and unknown SQLAlchemy failures are never retried.
    """
    if attempts < 1 or attempts > 5:
        raise ValueError("attempts must be between 1 and 5.")

    if delay_seconds < 0 or delay_seconds > 10:
        raise ValueError("delay_seconds must be between 0 and 10.")

    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except (OperationalError, SQLAlchemyTimeoutError) as exc:
            if attempt >= attempts:
                raise

            logger.warning(
                "Transient database operation failed; retrying.",
                extra={
                    "event": "database_operation_retry",
                    "attempt": attempt,
                    "max_attempts": attempts,
                    "error_type": type(exc).__name__,
                },
            )

            if delay_seconds:
                time.sleep(delay_seconds)

    raise RuntimeError("Database retry loop exited unexpectedly.")


# ---------------------------------------------------------------------------
# Connectivity and pool diagnostics
# ---------------------------------------------------------------------------

def check_database_connection() -> DatabaseConnectionStatus:
    """
    Execute a lightweight readiness query with bounded transient retries.

    The result contains no hostname, username, password, query payload or URL.
    """

    def _probe() -> None:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    try:
        execute_with_retry(_probe)

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


def get_database_pool_status() -> DatabaseStatusPayload:
    """
    Return safe SQLAlchemy pool metrics.

    Credentials and network location details are never exposed.
    """
    pool = engine.pool

    pool_size = _safe_pool_metric(pool, "size")
    checked_in = _safe_pool_metric(pool, "checkedin")
    checked_out = _safe_pool_metric(pool, "checkedout")
    overflow = _safe_pool_metric(pool, "overflow")

    effective_capacity = (
        pool_size + DB_MAX_OVERFLOW
        if not IS_SQLITE and pool_size is not None
        else None
    )

    exhausted = bool(
        effective_capacity is not None
        and checked_out is not None
        and checked_out >= effective_capacity
    )

    return {
        "enabled": not IS_SQLITE,
        "pool_type": type(pool).__name__,
        "pool_size": pool_size,
        "checked_in": checked_in,
        "checked_out": checked_out,
        "overflow": overflow,
        "max_overflow": DB_MAX_OVERFLOW if not IS_SQLITE else None,
        "effective_capacity": effective_capacity,
        "exhausted": exhausted,
        "timeout_seconds": (
            DB_POOL_TIMEOUT_SECONDS if not IS_SQLITE else None
        ),
        "recycle_seconds": (
            DB_POOL_RECYCLE_SECONDS if not IS_SQLITE else None
        ),
    }


def get_database_reliability_status() -> DatabaseStatusPayload:
    """Return the complete, safe database reliability report."""
    connection_status = check_database_connection()
    pool_status = get_database_pool_status()

    return {
        "connection_ok": connection_status.ok,
        "dialect": connection_status.dialect,
        "driver": connection_status.driver,
        "error_type": connection_status.error_type,
        "retryable": connection_status.retryable,
        "engine_initialized": engine is not None,
        "session_factory_initialized": SessionLocal is not None,
        "pool_enabled": pool_status["enabled"],
        "pool_pre_ping_enabled": bool(
            ENGINE_OPTIONS.get("pool_pre_ping", False)
        ),
        "future_mode_enabled": bool(
            ENGINE_OPTIONS.get("future", False)
        ),
        "transaction_safety_enabled": True,
        "timeout_protection_enabled": True,
        "active_sessions": get_active_session_count(),
        "pool_exhausted": pool_status["exhausted"],
        "connect_timeout_seconds": (
            DB_CONNECT_TIMEOUT_SECONDS if IS_POSTGRESQL else None
        ),
        "statement_timeout_ms": (
            DB_STATEMENT_TIMEOUT_MS if IS_POSTGRESQL else None
        ),
        "pool": pool_status,
    }


# ---------------------------------------------------------------------------
# Shutdown
# ---------------------------------------------------------------------------

def dispose_engine() -> None:
    """Close all pooled database connections."""
    engine.dispose()
