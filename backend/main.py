import asyncio
import base64
import hashlib
import json
import logging
import math
import os
import re
import ssl
import sys
import time
import uuid
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import NoReturn

import certifi
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
ssl._create_default_https_context = ssl.create_default_context(cafile=certifi.where())

load_dotenv()


def get_log_level() -> int:
    raw_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    level = getattr(logging, raw_level, None)

    if not isinstance(level, int):
        raise RuntimeError(
            "LOG_LEVEL must be one of: CRITICAL, ERROR, WARNING, INFO, DEBUG."
        )

    return level


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        extra_fields = (
            "request_id",
            "client_ip",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "event",
            "service",
            "operation",
            "attempt",
            "retry_delay_seconds",
            "retryable",
            "retry_after_seconds",
            "user_id",
            "paypal_event_type",
        )

        for field_name in extra_fields:
            field_value = getattr(record, field_name, None)
            if field_value is not None:
                payload[field_name] = field_value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(get_log_level())
    root_logger.addHandler(handler)

    logging.getLogger("uvicorn.access").disabled = True


configure_logging()

logger = logging.getLogger("talentmatch.api")

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,128}$")


def get_request_id(request: Request) -> str:
    incoming_request_id = request.headers.get("x-request-id", "").strip()

    if incoming_request_id and REQUEST_ID_PATTERN.fullmatch(incoming_request_id):
        return incoming_request_id

    return str(uuid.uuid4())


from auth import (
    get_current_user,
    get_firebase_resilience_status,
    get_test_user,
)
from billing.factory import get_billing_provider
from billing.paypal_provider import get_paypal_resilience_status
from config_validation import (
    get_configuration_validation_status,
    validate_startup_configuration,
)
from db import (
    Base,
    check_database_connection,
    classify_database_exception,
    dispose_engine,
    engine,
    get_database_pool_status,
    get_database_reliability_status,
    get_db,
    SessionLocal,
)
from models import AnalysisRecord, RecruiterCandidate, RecruiterJob, User
from observability import METRICS
from openai_service import (
    AIServiceError,
    analyze_cv_with_ai,
    get_openai_resilience_status,
    rewrite_cv_with_ai,
)
from pdf_report import build_analysis_pdf_report
from pdf_utils import extract_text_from_pdf
from recruiter_service import rank_candidates
from schemas import (
    AnalysisResponse,
    HistoryItemResponse,
    RecruiterJobCreateResponse,
    RecruiterJobStatusResponse,
)
from resilience import ExternalServiceError
from semantic_service import (
    analyze_semantic_match,
    get_semantic_resilience_status,
)
from storage import upload_pdf_to_firebase
from usage_service import ensure_analysis_allowed, get_user_usage


STARTUP_CONFIGURATION = validate_startup_configuration(logger)


try:
    Base.metadata.create_all(bind=engine)
except SQLAlchemyError:
    logger.exception(
        "Database schema initialization failed.",
        extra={
            "event": "database_schema_initialization_failed",
            "retryable": True,
        },
    )


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


def run_lightweight_migrations() -> None:
    migrations = [
        "ALTER TABLE users ADD COLUMN analyses_used INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN plan VARCHAR DEFAULT 'free'",
        "ALTER TABLE users ADD COLUMN is_pro BOOLEAN DEFAULT 0",
        "ALTER TABLE users ADD COLUMN paypal_customer_id VARCHAR",
        "ALTER TABLE users ADD COLUMN paypal_subscription_id VARCHAR",
        "ALTER TABLE users ADD COLUMN paypal_subscription_status VARCHAR",
        "ALTER TABLE analysis_records ADD COLUMN analysis_type VARCHAR DEFAULT 'cv_analysis'",

        # TalentMatch Pro v2.0 - Recruiter Workspace / Candidate Database.
        # This table stores every candidate returned by Recruiter Mode, not only the top result.
        """
        CREATE TABLE IF NOT EXISTS recruiter_candidates (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            filename VARCHAR(255) NOT NULL,
            cv_storage_path VARCHAR(500),
            job_description TEXT NOT NULL,
            rank INTEGER DEFAULT 0,
            score INTEGER DEFAULT 0,
            match_score INTEGER DEFAULT 0,
            combined_score INTEGER DEFAULT 0,
            semantic_score INTEGER DEFAULT 0,
            keyword_score INTEGER DEFAULT 0,
            verdict VARCHAR(100) DEFAULT '',
            summary TEXT DEFAULT '',
            matched_skills TEXT DEFAULT '[]',
            missing_skills TEXT DEFAULT '[]',
            recommendations TEXT DEFAULT '[]',
            matched_keywords TEXT DEFAULT '[]',
            missing_keywords TEXT DEFAULT '[]',
            favorite BOOLEAN DEFAULT FALSE,
            status VARCHAR(50) DEFAULT 'new',
            notes TEXT DEFAULT '',
            tags TEXT DEFAULT '[]',
            source VARCHAR(100) DEFAULT 'recruiter_mode',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_recruiter_candidates_user_id ON recruiter_candidates (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_recruiter_candidates_filename ON recruiter_candidates (filename)",
        "CREATE INDEX IF NOT EXISTS ix_recruiter_candidates_rank ON recruiter_candidates (rank)",
        "CREATE INDEX IF NOT EXISTS ix_recruiter_candidates_score ON recruiter_candidates (score)",
        "CREATE INDEX IF NOT EXISTS ix_recruiter_candidates_favorite ON recruiter_candidates (favorite)",
        "CREATE INDEX IF NOT EXISTS ix_recruiter_candidates_status ON recruiter_candidates (status)",
        "CREATE INDEX IF NOT EXISTS ix_recruiter_candidates_created_at ON recruiter_candidates (created_at)",
        "CREATE INDEX IF NOT EXISTS ix_recruiter_jobs_user_id ON recruiter_jobs (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_recruiter_jobs_job_id ON recruiter_jobs (job_id)",
        "CREATE INDEX IF NOT EXISTS ix_recruiter_jobs_status ON recruiter_jobs (status)",
        "CREATE INDEX IF NOT EXISTS ix_recruiter_jobs_created_at ON recruiter_jobs (created_at)",
    ]

    for migration in migrations:
        try:
            with engine.begin() as conn:
                conn.execute(text(migration))
        except Exception:
            pass


run_lightweight_migrations()


def get_environment() -> str:
    return os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development")).strip().lower()


def env_flag(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def should_force_https() -> bool:
    default = get_environment() in {"production", "prod"}
    return env_flag("FORCE_HTTPS", default=default)


def should_enable_hsts() -> bool:
    default = get_environment() in {"production", "prod"}
    return env_flag("ENABLE_HSTS", default=default)


def get_hsts_max_age() -> int:
    raw_value = os.getenv("HSTS_MAX_AGE", "31536000").strip()

    try:
        max_age = int(raw_value)
    except ValueError as exc:
        raise RuntimeError("HSTS_MAX_AGE must be a valid integer.") from exc

    if max_age < 0:
        raise RuntimeError("HSTS_MAX_AGE cannot be negative.")

    return max_age


def get_api_content_security_policy() -> str:
    return os.getenv(
        "API_CONTENT_SECURITY_POLICY",
        "; ".join(
            [
                "default-src 'none'",
                "base-uri 'none'",
                "frame-ancestors 'none'",
                "form-action 'none'",
            ]
        ),
    ).strip()


def get_docs_content_security_policy() -> str:
    return os.getenv(
        "DOCS_CONTENT_SECURITY_POLICY",
        "; ".join(
            [
                "default-src 'self'",
                "base-uri 'self'",
                "frame-ancestors 'none'",
                "form-action 'self'",
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
                "img-src 'self' data: https://fastapi.tiangolo.com",
                "font-src 'self' data: https://cdn.jsdelivr.net",
                "connect-src 'self'",
            ]
        ),
    ).strip()



class ResponseOptimizationMiddleware:
    """
    Adds safe cache policy, weak ETags and conditional GET support.

    ETags are limited to small public or documentation responses. Private and
    user-specific API responses always receive Cache-Control: no-store.
    Streaming and download responses are never buffered or modified.
    """

    PUBLIC_CACHE_POLICIES = {
        "/robots.txt": "public, max-age=3600, stale-while-revalidate=86400",
        "/sitemap.xml": "public, max-age=3600, stale-while-revalidate=86400",
        "/openapi.json": "public, max-age=300, stale-while-revalidate=3600",
    }

    ETAG_PATHS = {
        "/robots.txt",
        "/sitemap.xml",
        "/openapi.json",
    }

    NO_STORE_PATHS = {
        "/",
        "/healthz",
        "/readyz",
        "/metrics",
        "/error-test",
    }

    MAX_ETAG_BODY_BYTES = 1_048_576

    def __init__(self, app):
        self.app = app

    @staticmethod
    def _headers_to_dict(headers: list[tuple[bytes, bytes]]) -> dict[bytes, bytes]:
        return {name.lower(): value for name, value in headers}

    @staticmethod
    def _replace_header(
        headers: list[tuple[bytes, bytes]],
        name: bytes,
        value: bytes,
    ) -> list[tuple[bytes, bytes]]:
        lowered_name = name.lower()
        updated = [
            (header_name, header_value)
            for header_name, header_value in headers
            if header_name.lower() != lowered_name
        ]
        updated.append((name, value))
        return updated

    @staticmethod
    def _remove_headers(
        headers: list[tuple[bytes, bytes]],
        names: set[bytes],
    ) -> list[tuple[bytes, bytes]]:
        lowered_names = {name.lower() for name in names}
        return [
            (header_name, header_value)
            for header_name, header_value in headers
            if header_name.lower() not in lowered_names
        ]

    @staticmethod
    def _weak_etag(body: bytes) -> str:
        digest = hashlib.sha256(body).hexdigest()
        return f'W/"{digest}"'

    @staticmethod
    def _normalize_etag(value: str) -> str:
        normalized = value.strip()

        if normalized.lower().startswith("w/"):
            normalized = normalized[2:].strip()

        if len(normalized) >= 2 and normalized[0] == '"' and normalized[-1] == '"':
            normalized = normalized[1:-1]

        return normalized.strip()

    @classmethod
    def _etag_matches(cls, if_none_match: str, etag: str) -> bool:
        expected = cls._normalize_etag(etag)

        for candidate in if_none_match.split(","):
            candidate = candidate.strip()

            if not candidate:
                continue

            if candidate == "*":
                return True

            if cls._normalize_etag(candidate) == expected:
                return True

        return False

    def _cache_control_for(self, path: str, method: str) -> str:
        if path in self.PUBLIC_CACHE_POLICIES:
            return self.PUBLIC_CACHE_POLICIES[path]

        if path in self.NO_STORE_PATHS:
            return "no-store"

        if method in {"GET", "HEAD"}:
            return "private, no-store"

        return "no-store"

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET").upper()
        path = scope.get("path", "")
        request_headers = {
            name.lower(): value
            for name, value in scope.get("headers", [])
        }

        should_build_etag = method in {"GET", "HEAD"} and path in self.ETAG_PATHS

        if not should_build_etag:
            async def send_with_cache(message):
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    header_map = self._headers_to_dict(headers)

                    if b"cache-control" not in header_map:
                        headers.append(
                            (
                                b"cache-control",
                                self._cache_control_for(path, method).encode("latin-1"),
                            )
                        )

                    message["headers"] = headers

                await send(message)

            await self.app(scope, receive, send_with_cache)
            return

        start_message = None
        body_chunks: list[bytes] = []
        body_size = 0
        passthrough = False

        async def capture_send(message):
            nonlocal start_message, body_size, passthrough

            if passthrough:
                await send(message)
                return

            if message["type"] == "http.response.start":
                start_message = {
                    "type": "http.response.start",
                    "status": message["status"],
                    "headers": list(message.get("headers", [])),
                }
                return

            if message["type"] == "http.response.body":
                chunk = message.get("body", b"")
                body_size += len(chunk)

                if body_size > self.MAX_ETAG_BODY_BYTES:
                    passthrough = True

                    if start_message is not None:
                        headers = list(start_message.get("headers", []))
                        header_map = self._headers_to_dict(headers)
                        if b"cache-control" not in header_map:
                            headers.append(
                                (
                                    b"cache-control",
                                    self._cache_control_for(path, method).encode("latin-1"),
                                )
                            )
                        start_message["headers"] = headers
                        await send(start_message)

                    for buffered_chunk in body_chunks:
                        await send(
                            {
                                "type": "http.response.body",
                                "body": buffered_chunk,
                                "more_body": True,
                            }
                        )

                    await send(message)
                    return

                body_chunks.append(chunk)

                if message.get("more_body", False):
                    return

                if start_message is None:
                    await send(message)
                    return

                status_code = int(start_message["status"])
                body = b"".join(body_chunks)
                headers = list(start_message.get("headers", []))
                header_map = self._headers_to_dict(headers)

                if b"cache-control" not in header_map:
                    headers.append(
                        (
                            b"cache-control",
                            self._cache_control_for(path, method).encode("latin-1"),
                        )
                    )

                content_type = header_map.get(b"content-type", b"").decode(
                    "latin-1",
                    errors="ignore",
                )

                can_etag = (
                    status_code == 200
                    and body
                    and (
                        content_type.startswith("application/json")
                        or content_type.startswith("text/")
                        or content_type.startswith("application/xml")
                    )
                )

                if can_etag:
                    etag = self._weak_etag(body)
                    headers = self._replace_header(
                        headers,
                        b"etag",
                        etag.encode("latin-1"),
                    )

                    vary_value = header_map.get(b"vary", b"").decode(
                        "latin-1",
                        errors="ignore",
                    )
                    vary_tokens = {
                        token.strip()
                        for token in vary_value.split(",")
                        if token.strip()
                    }
                    vary_tokens.add("Accept-Encoding")
                    headers = self._replace_header(
                        headers,
                        b"vary",
                        ", ".join(sorted(vary_tokens)).encode("latin-1"),
                    )

                    incoming_etag = request_headers.get(b"if-none-match", b"").decode(
                        "latin-1",
                        errors="ignore",
                    )

                    if incoming_etag and self._etag_matches(incoming_etag, etag):
                        headers = self._remove_headers(
                            headers,
                            {
                                b"content-length",
                                b"content-type",
                                b"content-encoding",
                            },
                        )
                        await send(
                            {
                                "type": "http.response.start",
                                "status": 304,
                                "headers": headers,
                            }
                        )
                        await send(
                            {
                                "type": "http.response.body",
                                "body": b"",
                                "more_body": False,
                            }
                        )
                        return

                headers = self._replace_header(
                    headers,
                    b"content-length",
                    str(len(body)).encode("latin-1"),
                )
                start_message["headers"] = headers
                await send(start_message)
                await send(
                    {
                        "type": "http.response.body",
                        "body": b"" if method == "HEAD" else body,
                        "more_body": False,
                    }
                )

        await self.app(scope, receive, capture_send)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = get_request_id(request)
        client_ip = get_client_ip(request)
        started_at = time.perf_counter()

        request.state.request_id = request_id

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            METRICS.record_request(
                path=request.url.path,
                status_code=500,
                duration_ms=duration_ms,
            )
            logger.exception(
                "Unhandled request exception.",
                extra={
                    "request_id": request_id,
                    "client_ip": client_ip,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "duration_ms": duration_ms,
                    "event": "request_failed",
                },
            )
            raise

        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        response.headers["X-Request-ID"] = request_id

        METRICS.record_request(
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        log_method = logger.warning if response.status_code >= 400 else logger.info
        log_method(
            "HTTP request completed.",
            extra={
                "request_id": request_id,
                "client_ip": client_ip,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "event": "request_completed",
            },
        )

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        request_path = request.url.path
        is_docs_route = (
            request_path == "/docs"
            or request_path.startswith("/docs/")
            or request_path == "/redoc"
            or request_path.startswith("/redoc/")
            or request_path == "/openapi.json"
        )

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), autoplay=(), camera=(), display-capture=(), "
            "encrypted-media=(), fullscreen=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), midi=(), payment=(), "
            "picture-in-picture=(), publickey-credentials-get=(), usb=()"
        )
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
        response.headers["Content-Security-Policy"] = (
            get_docs_content_security_policy()
            if is_docs_route
            else get_api_content_security_policy()
        )

        if should_enable_hsts():
            response.headers["Strict-Transport-Security"] = (
                f"max-age={get_hsts_max_age()}; includeSubDomains"
            )

        return response



def get_positive_int_env(name: str, default: int, *, minimum: int = 1) -> int:
    raw_value = os.getenv(name, str(default)).strip()

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a valid integer.") from exc

    if value < minimum:
        raise RuntimeError(f"{name} must be at least {minimum}.")

    return value


@dataclass(frozen=True)
class RateLimitRule:
    name: str
    requests: int
    window_seconds: int


class InMemoryRateLimitStore:
    """
    Process-local sliding-window limiter.

    TalentMatch Pro currently runs one backend process per Render service
    instance, so this store provides deterministic protection without adding
    another infrastructure dependency. The interface is intentionally isolated
    so it can be replaced by Redis in a later horizontal-scaling phase without
    changing route code.
    """

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._violations: dict[str, deque[float]] = defaultdict(deque)
        self._blocked_until: dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._last_cleanup = 0.0

    async def check(
        self,
        *,
        key: str,
        limit: int,
        window_seconds: int,
        strike_threshold: int,
        strike_window_seconds: int,
        block_seconds: int,
    ) -> tuple[bool, int, int, bool]:
        now = time.monotonic()

        async with self._lock:
            self._cleanup_if_needed(now)

            blocked_until = self._blocked_until.get(key, 0.0)
            if blocked_until > now:
                retry_after = max(1, int(blocked_until - now))
                return False, 0, retry_after, True

            if blocked_until:
                self._blocked_until.pop(key, None)

            events = self._events[key]
            cutoff = now - window_seconds

            while events and events[0] <= cutoff:
                events.popleft()

            if len(events) >= limit:
                retry_after = max(1, int(window_seconds - (now - events[0])))

                violations = self._violations[key]
                violation_cutoff = now - strike_window_seconds
                while violations and violations[0] <= violation_cutoff:
                    violations.popleft()

                violations.append(now)

                if len(violations) >= strike_threshold:
                    self._blocked_until[key] = now + block_seconds
                    violations.clear()
                    return False, 0, block_seconds, True

                return False, 0, retry_after, False

            events.append(now)
            remaining = max(0, limit - len(events))
            return True, remaining, window_seconds, False

    def _cleanup_if_needed(self, now: float) -> None:
        if now - self._last_cleanup < 300:
            return

        self._last_cleanup = now

        expired_blocks = [
            key for key, blocked_until in self._blocked_until.items()
            if blocked_until <= now
        ]
        for key in expired_blocks:
            self._blocked_until.pop(key, None)

        stale_event_keys = [
            key for key, events in self._events.items()
            if not events or now - events[-1] > 3600
        ]
        for key in stale_event_keys:
            self._events.pop(key, None)

        stale_violation_keys = [
            key for key, violations in self._violations.items()
            if not violations or now - violations[-1] > 3600
        ]
        for key in stale_violation_keys:
            self._violations.pop(key, None)


RATE_LIMIT_STORE = InMemoryRateLimitStore()


def rate_limiting_enabled() -> bool:
    return env_flag("RATE_LIMIT_ENABLED", default=True)


def get_client_ip(request: Request) -> str:
    cf_connecting_ip = request.headers.get("cf-connecting-ip", "").strip()
    if cf_connecting_ip:
        return cf_connecting_ip

    forwarded_for = request.headers.get("x-forwarded-for", "").strip()
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()

    if request.client and request.client.host:
        return request.client.host

    return "unknown"


def get_rate_limit_rule(path: str, method: str) -> RateLimitRule | None:
    public_unlimited_paths = {
        "/healthz",
        "/readyz",
        "/metrics",
        "/robots.txt",
        "/sitemap.xml",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    if path in public_unlimited_paths or path.startswith("/docs/") or path.startswith("/redoc/"):
        return None

    if path in {"/billing/webhook", "/paypal/webhook"}:
        return RateLimitRule(
            name="webhook",
            requests=get_positive_int_env("RATE_LIMIT_WEBHOOK_REQUESTS", 120),
            window_seconds=get_positive_int_env("RATE_LIMIT_WEBHOOK_WINDOW_SECONDS", 60),
        )

    if path in {"/analyze-test", "/ats-test", "/history-test"}:
        return RateLimitRule(
            name="test",
            requests=get_positive_int_env("RATE_LIMIT_TEST_REQUESTS", 10),
            window_seconds=get_positive_int_env("RATE_LIMIT_TEST_WINDOW_SECONDS", 60),
        )

    ai_paths = {
        "/analyze-resume",
        "/ats-check",
        "/semantic-match",
        "/recruiter/rank-candidates",
        "/rewrite-cv",
        "/reports/analysis-pdf",
    }
    if path in ai_paths:
        return RateLimitRule(
            name="ai",
            requests=get_positive_int_env("RATE_LIMIT_AI_REQUESTS", 20),
            window_seconds=get_positive_int_env("RATE_LIMIT_AI_WINDOW_SECONDS", 60),
        )

    billing_paths = {
        "/billing/create-checkout",
        "/billing/create-portal",
        "/billing/demo-upgrade",
    }
    if path in billing_paths:
        return RateLimitRule(
            name="billing",
            requests=get_positive_int_env("RATE_LIMIT_BILLING_REQUESTS", 20),
            window_seconds=get_positive_int_env("RATE_LIMIT_BILLING_WINDOW_SECONDS", 60),
        )

    if method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
        return RateLimitRule(
            name="write",
            requests=get_positive_int_env("RATE_LIMIT_WRITE_REQUESTS", 60),
            window_seconds=get_positive_int_env("RATE_LIMIT_WRITE_WINDOW_SECONDS", 60),
        )

    return RateLimitRule(
        name="default",
        requests=get_positive_int_env("RATE_LIMIT_DEFAULT_REQUESTS", 180),
        window_seconds=get_positive_int_env("RATE_LIMIT_DEFAULT_WINDOW_SECONDS", 60),
    )


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not rate_limiting_enabled() or request.method.upper() == "OPTIONS":
            return await call_next(request)

        rule = get_rate_limit_rule(request.url.path, request.method)
        if rule is None:
            return await call_next(request)

        client_ip = get_client_ip(request)
        rate_limit_key = f"{client_ip}:{rule.name}"

        allowed, remaining, retry_after, blocked = await RATE_LIMIT_STORE.check(
            key=rate_limit_key,
            limit=rule.requests,
            window_seconds=rule.window_seconds,
            strike_threshold=get_positive_int_env("RATE_LIMIT_STRIKE_THRESHOLD", 3),
            strike_window_seconds=get_positive_int_env(
                "RATE_LIMIT_STRIKE_WINDOW_SECONDS",
                300,
            ),
            block_seconds=get_positive_int_env("RATE_LIMIT_BLOCK_SECONDS", 300),
        )

        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={
                    "detail": {
                        "message": (
                            "Too many requests. Access is temporarily blocked."
                            if blocked
                            else "Too many requests. Please try again later."
                        ),
                        "type": "rate_limit_exceeded",
                        "scope": rule.name,
                        "retry_after_seconds": retry_after,
                    }
                },
            )
            response.headers["Retry-After"] = str(retry_after)
            response.headers["X-RateLimit-Limit"] = str(rule.requests)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(retry_after)
            return response

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(rule.requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(rule.window_seconds)
        return response



def request_id_from_state(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)

    if isinstance(request_id, str) and REQUEST_ID_PATTERN.fullmatch(request_id):
        return request_id

    request_id = get_request_id(request)
    request.state.request_id = request_id
    return request_id


def error_message_from_detail(detail: object, fallback: str) -> str:
    if isinstance(detail, str) and detail.strip():
        return detail.strip()

    if isinstance(detail, dict):
        message = detail.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()

    return fallback


def build_error_response(
    *,
    request: Request,
    status_code: int,
    error_type: str,
    message: str,
    detail: object,
    details: object | None = None,
    headers: dict[str, str] | None = None,
    service: str | None = None,
    retryable: bool | None = None,
    retry_after_seconds: int | None = None,
) -> JSONResponse:
    request_id = request_id_from_state(request)
    timestamp = datetime.now(timezone.utc).isoformat()

    error_payload: dict[str, object] = {
        "type": error_type,
        "error_code": error_type,
        "message": message,
        "status_code": status_code,
        "request_id": request_id,
        "timestamp": timestamp,
    }

    if service:
        error_payload["service"] = service

    if retryable is not None:
        error_payload["retryable"] = retryable

    if retry_after_seconds is not None:
        error_payload["retry_after_seconds"] = retry_after_seconds

    if details is not None:
        error_payload["details"] = details

    response_headers = dict(headers or {})

    if retry_after_seconds is not None:
        response_headers["Retry-After"] = str(retry_after_seconds)

    response = JSONResponse(
        status_code=status_code,
        content={
            "detail": detail,
            "error": error_payload,
        },
        headers=response_headers,
    )
    response.headers["X-Request-ID"] = request_id
    return response


RECRUITER_JOB_EXECUTOR = ThreadPoolExecutor(
    max_workers=get_positive_int_env("RECRUITER_JOB_WORKERS", 1),
    thread_name_prefix="recruiter-job",
)


def recruiter_job_to_dict(job: RecruiterJob, *, include_result: bool = True) -> dict:
    result = None
    if include_result and job.result_payload:
        try:
            parsed_result = json.loads(job.result_payload)
            result = parsed_result if isinstance(parsed_result, dict) else None
        except json.JSONDecodeError:
            result = None

    return {
        "job_id": job.job_id,
        "status": job.status,
        "progress": max(0, min(100, int(job.progress or 0))),
        "total_candidates": int(job.total_candidates or 0),
        "processed_candidates": int(job.processed_candidates or 0),
        "result": result,
        "error_message": job.error_message,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "updated_at": job.updated_at,
    }


def process_recruiter_job(job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.query(RecruiterJob).filter(RecruiterJob.job_id == job_id).first()
        if job is None or job.status == "completed":
            return

        active_job = job
        processing_started_at = datetime.now(timezone.utc)

        active_job.status = "processing"
        active_job.started_at = active_job.started_at or processing_started_at
        active_job.error_message = None
        active_job.updated_at = processing_started_at
        db.commit()

        payload = json.loads(active_job.input_payload)
        candidates = payload.get("candidates") or []
        first_pdf_base64 = payload.get("first_pdf_base64")
        first_pdf_bytes = (
            base64.b64decode(first_pdf_base64)
            if isinstance(first_pdf_base64, str) and first_pdf_base64
            else None
        )

        if not isinstance(candidates, list) or not candidates:
            raise ValueError("Recruiter job contains no candidates.")

        def update_progress(processed: int, total: int) -> None:
            active_job.processed_candidates = processed
            active_job.total_candidates = total
            active_job.progress = min(
                99,
                max(1, round((processed / max(total, 1)) * 95)),
            )
            active_job.updated_at = datetime.now(timezone.utc)
            db.commit()

        result = rank_candidates(
            candidates=candidates,
            job_description=active_job.job_description,
            progress_callback=update_progress,
        )

        ranked_candidates = result.get("candidates", result.get("ranked_candidates", []))
        top_candidate = ranked_candidates[0] if ranked_candidates else {}
        top_filename = top_candidate.get("filename", payload.get("first_filename", "candidate.pdf"))
        top_score = top_candidate.get("score", result.get("score", 0))
        current_user = db.query(User).filter(User.id == job.user_id).first()
        if current_user is None:
            raise ValueError("Recruiter job owner no longer exists.")

        create_analysis_history_record(
            db,
            current_user,
            analysis_type="recruiter_mode",
            cv_filename=top_filename,
            pdf_bytes=first_pdf_bytes,
            job_description=job.job_description,
            score=top_score,
            summary=first_nonempty_text(
                top_candidate.get("summary"),
                result.get("summary"),
                f"Recruiter ranking completed for {len(candidates)} candidate(s). Top candidate: {top_filename}.",
            ),
            matched_skills=first_nonempty_history_list(
                top_candidate.get("matched_skills"),
                top_candidate.get("strengths"),
                result.get("matched_skills"),
                result.get("strengths"),
            ),
            missing_skills=first_nonempty_history_list(
                top_candidate.get("missing_skills"),
                top_candidate.get("weaknesses"),
                result.get("missing_skills"),
                result.get("weaknesses"),
            ),
            recommendations=first_nonempty_history_list(
                top_candidate.get("recommendations"),
                result.get("recommendations"),
            ),
        )

        completed_job = (
            db.query(RecruiterJob)
            .filter(RecruiterJob.job_id == job_id)
            .first()
        )
        if completed_job is None:
            return

        completed_at = datetime.now(timezone.utc)
        completed_job.status = "completed"
        completed_job.progress = 100
        completed_job.processed_candidates = completed_job.total_candidates
        completed_job.result_payload = json.dumps(result, ensure_ascii=False)
        completed_job.input_payload = "{}"
        completed_job.completed_at = completed_at
        completed_job.updated_at = completed_at
        db.commit()
        logger.info(
            "Recruiter batch job completed.",
            extra={
                "event": "recruiter_job_completed",
                "user_id": completed_job.user_id,
                "operation": job_id,
            },
        )
    except Exception:
        db.rollback()
        failed_job = (
            db.query(RecruiterJob)
            .filter(RecruiterJob.job_id == job_id)
            .first()
        )
        if failed_job is not None:
            failed_at = datetime.now(timezone.utc)
            failed_job.status = "failed"
            failed_job.error_message = (
                "Recruiter ranking could not be completed. Please retry the batch."
            )
            failed_job.completed_at = failed_at
            failed_job.updated_at = failed_at
            db.commit()
        logger.exception(
            "Recruiter batch job failed.",
            extra={"event": "recruiter_job_failed", "operation": job_id, "retryable": True},
        )
    finally:
        db.close()


def submit_recruiter_job(job_id: str) -> None:
    RECRUITER_JOB_EXECUTOR.submit(process_recruiter_job, job_id)


def recover_recruiter_jobs() -> None:
    db = SessionLocal()
    try:
        jobs = (
            db.query(RecruiterJob)
            .filter(RecruiterJob.status.in_(["queued", "processing"]))
            .order_by(RecruiterJob.created_at.asc())
            .all()
        )
        for job in jobs:
            job.status = "queued"
            job.progress = min(int(job.progress or 0), 99)
            db.commit()
            submit_recruiter_job(job.job_id)
    finally:
        db.close()


app = FastAPI(title="TalentMatch Pro API", version="0.1.0")


@app.on_event("startup")
def startup_recruiter_jobs() -> None:
    recover_recruiter_jobs()


@app.on_event("shutdown")
def shutdown_database_engine() -> None:
    RECRUITER_JOB_EXECUTOR.shutdown(wait=False, cancel_futures=False)
    dispose_engine()
    logger.info(
        "Database engine disposed.",
        extra={"event": "database_engine_disposed"},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    detail = exc.detail
    message = error_message_from_detail(
        detail,
        "The request could not be completed.",
    )

    error_type = "http_error"
    service = None
    retryable = None
    retry_after_seconds = None

    if isinstance(detail, dict):
        detail_type = detail.get("type")
        if isinstance(detail_type, str) and detail_type.strip():
            error_type = detail_type.strip()

        detail_service = detail.get("service")
        if isinstance(detail_service, str) and detail_service.strip():
            service = detail_service.strip()

        detail_retryable = detail.get("retryable")
        if isinstance(detail_retryable, bool):
            retryable = detail_retryable

        detail_retry_after = detail.get("retry_after_seconds")
        if isinstance(detail_retry_after, int) and detail_retry_after > 0:
            retry_after_seconds = detail_retry_after

    return build_error_response(
        request=request,
        status_code=exc.status_code,
        error_type=error_type,
        message=message,
        detail=detail,
        headers=dict(exc.headers or {}),
        service=service,
        retryable=retryable,
        retry_after_seconds=retry_after_seconds,
    )


@app.exception_handler(ExternalServiceError)
async def external_service_exception_handler(
    request: Request,
    exc: ExternalServiceError,
) -> JSONResponse:
    request_id = request_id_from_state(request)

    logger.warning(
        "External service request failed.",
        extra={
            "request_id": request_id,
            "client_ip": get_client_ip(request),
            "method": request.method,
            "path": request.url.path,
            "status_code": exc.status_code,
            "event": "external_service_error",
            "service": exc.service,
            "retryable": exc.retryable,
            "retry_after_seconds": exc.retry_after_seconds,
        },
    )

    return build_error_response(
        request=request,
        status_code=exc.status_code,
        error_type=exc.error_code,
        message=exc.message,
        detail={
            "message": exc.message,
            "type": exc.error_code,
            "service": exc.service,
            "retryable": exc.retryable,
            "retry_after_seconds": exc.retry_after_seconds,
        },
        service=exc.service,
        retryable=exc.retryable,
        retry_after_seconds=exc.retry_after_seconds,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    validation_errors = exc.errors()

    return build_error_response(
        request=request,
        status_code=422,
        error_type="validation_error",
        message="Request validation failed.",
        detail=validation_errors,
        details=validation_errors,
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(
    request: Request,
    exc: SQLAlchemyError,
) -> JSONResponse:
    request_id = request_id_from_state(request)
    error_info = classify_database_exception(exc)

    log_method = (
        logger.warning
        if error_info.status_code in {409, 503, 504}
        else logger.error
    )
    log_method(
        "Database operation failed.",
        extra={
            "request_id": request_id,
            "client_ip": get_client_ip(request),
            "method": request.method,
            "path": request.url.path,
            "status_code": error_info.status_code,
            "event": "database_operation_failed",
            "service": "PostgreSQL",
            "retryable": error_info.retryable,
        },
    )

    return build_error_response(
        request=request,
        status_code=error_info.status_code,
        error_type=error_info.error_type,
        message=error_info.message,
        detail={
            "message": error_info.message,
            "type": error_info.error_type,
            "service": "PostgreSQL",
            "retryable": error_info.retryable,
        },
        service="PostgreSQL",
        retryable=error_info.retryable,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    request_id = request_id_from_state(request)

    logger.exception(
        "Unhandled application exception.",
        extra={
            "request_id": request_id,
            "client_ip": get_client_ip(request),
            "method": request.method,
            "path": request.url.path,
            "status_code": 500,
            "event": "unhandled_exception",
        },
    )

    return build_error_response(
        request=request,
        status_code=500,
        error_type="internal_server_error",
        message="An unexpected server error occurred.",
        detail="An unexpected server error occurred.",
    )


def get_allowed_hosts() -> list[str]:
    raw = os.getenv(
        "ALLOWED_HOSTS",
        ",".join(
            [
                "localhost",
                "127.0.0.1",
                "backend",
                "testserver",
                "api.talentmatchcv.com",
                "talentmatchcv.com",
                "www.talentmatchcv.com",
                "*.talentmatchcv.com",
                "*.onrender.com",
            ]
        ),
    )

    hosts = []
    for host in raw.split(","):
        normalized = host.strip().lower().rstrip(".")
        if normalized and normalized not in hosts:
            hosts.append(normalized)

    if not hosts:
        raise RuntimeError("ALLOWED_HOSTS must contain at least one trusted host.")

    return hosts


def get_cors_origins() -> list[str]:
    raw = os.getenv(
        "CORS_ORIGINS",
        ",".join(
            [
                "http://localhost:8501",
                "http://127.0.0.1:8501",
                "https://talentmatchcv.com",
                "https://www.talentmatchcv.com",
                "https://talentmatch-frontend-dejan.onrender.com",
            ]
        ),
    )
    return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]


app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    GZipMiddleware,
    minimum_size=get_positive_int_env("GZIP_MINIMUM_SIZE", 500),
    compresslevel=get_positive_int_env("GZIP_COMPRESS_LEVEL", 6),
)
app.add_middleware(ResponseOptimizationMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=get_allowed_hosts(),
    www_redirect=False,
)

if should_force_https():
    app.add_middleware(HTTPSRedirectMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "PAYPAL-TRANSMISSION-ID",
        "PAYPAL-TRANSMISSION-TIME",
        "PAYPAL-CERT-URL",
        "PAYPAL-AUTH-ALGO",
        "PAYPAL-TRANSMISSION-SIG",
    ],
)


def get_resilience_status() -> dict[str, dict[str, object]]:
    return {
        "openai": get_openai_resilience_status(),
        "openai_semantic": get_semantic_resilience_status(),
        "paypal": get_paypal_resilience_status(),
        "firebase_authentication": get_firebase_resilience_status(),
    }


def resilience_is_available(
    statuses: dict[str, dict[str, object]],
) -> bool:
    return all(
        status.get("state") != "open"
        for status in statuses.values()
    )


def config_status() -> dict:
    database_url = os.getenv("DATABASE_URL", "").strip()
    firebase_credentials = os.getenv("FIREBASE_CREDENTIALS", "").strip()
    google_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    configuration_validation = get_configuration_validation_status()
    resilience_status = get_resilience_status()

    return {
        "environment": get_environment(),
        "https_redirect_enabled": should_force_https(),
        "hsts_enabled": should_enable_hsts(),
        "security_headers_enabled": True,
        "production_logging_enabled": True,
        "request_id_enabled": True,
        "exception_handling_enabled": True,
        "standard_error_responses_enabled": True,
        "observability_enabled": True,
        "metrics_endpoint_enabled": True,
        "gzip_compression_enabled": True,
        "gzip_minimum_size": get_positive_int_env("GZIP_MINIMUM_SIZE", 500),
        "etag_enabled": True,
        "conditional_get_enabled": True,
        "cache_control_enabled": True,
        "database_configuration_validation_enabled": True,
        "database_transaction_safety_enabled": True,
        "database_timeout_protection_enabled": True,
        "api_reliability_enabled": True,
        "graceful_degradation_enabled": True,
        "retry_policy_enabled": True,
        "circuit_breaker_enabled": True,
        "external_services_available": resilience_is_available(
            resilience_status
        ),
        "external_service_circuits": resilience_status,
        "startup_configuration_validation_enabled": True,
        "startup_configuration_valid": configuration_validation["valid"],
        "startup_configuration_error_count": configuration_validation["error_count"],
        "startup_configuration_warning_count": configuration_validation["warning_count"],
        "secrets_logged": False,
        "uptime_seconds": METRICS.snapshot(
            environment=get_environment()
        )["uptime_seconds"],
        "log_level": logging.getLevelName(get_log_level()),
        "rate_limiting_enabled": rate_limiting_enabled(),
        "rate_limit_store": "in_memory_single_instance",
        "rate_limit_ai_requests": get_positive_int_env("RATE_LIMIT_AI_REQUESTS", 20),
        "rate_limit_ai_window_seconds": get_positive_int_env(
            "RATE_LIMIT_AI_WINDOW_SECONDS",
            60,
        ),
        "rate_limit_block_seconds": get_positive_int_env(
            "RATE_LIMIT_BLOCK_SECONDS",
            300,
        ),
        "trusted_hosts_count": len(get_allowed_hosts()),
        "database_configured": bool(database_url),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY", "").strip()),
        "firebase_project_configured": bool(os.getenv("FIREBASE_PROJECT_ID", "").strip()),
        "firebase_storage_configured": bool(os.getenv("FIREBASE_STORAGE_BUCKET", "").strip()),
        "firebase_credentials_configured": bool(firebase_credentials or google_credentials),
        "billing_provider": os.getenv("BILLING_PROVIDER", "paypal"),
        "paypal_client_configured": bool(os.getenv("PAYPAL_CLIENT_ID", "").strip()),
        "paypal_secret_configured": bool(os.getenv("PAYPAL_CLIENT_SECRET", "").strip()),
        "paypal_plan_configured": bool(os.getenv("PAYPAL_PLAN_ID", "").strip()),
        "paypal_webhook_configured": bool(os.getenv("PAYPAL_WEBHOOK_ID", "").strip()),
        "paypal_environment": os.getenv("PAYPAL_ENV", "live"),
        "frontend_url_configured": bool(os.getenv("FRONTEND_URL", "").strip()),
        "cors_origins_count": len(get_cors_origins()),
    }


def parse_json_list(value: str) -> list[str]:
    try:
        data = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    return [str(item).strip() for item in data if str(item).strip()]


def raise_ai_http_exception(exc: AIServiceError) -> NoReturn:
    detail = {
        "message": exc.message,
        "type": exc.error_code,
        "service": exc.service,
        "retryable": exc.retryable,
        "retry_after_seconds": exc.retry_after_seconds,
    }

    headers = None
    if exc.retry_after_seconds is not None:
        headers = {
            "Retry-After": str(exc.retry_after_seconds),
        }

    raise HTTPException(
        status_code=exc.status_code,
        detail=detail,
        headers=headers,
    )


class CandidateCreateRequest(BaseModel):
    filename: str = Field(default="candidate.pdf")
    cv_storage_path: str | None = None
    job_description: str = Field(default="")
    rank: int = 0
    score: int = 0
    match_score: int = 0
    combined_score: int = 0
    semantic_score: int = 0
    keyword_score: int = 0
    verdict: str = ""
    summary: str = ""
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    favorite: bool = False
    status: str = "new"
    notes: str = ""
    tags: list[str] = Field(default_factory=list)


class CandidateUpdateRequest(BaseModel):
    filename: str | None = None
    cv_storage_path: str | None = None
    job_description: str | None = None
    rank: int | None = None
    score: int | None = None
    match_score: int | None = None
    combined_score: int | None = None
    semantic_score: int | None = None
    keyword_score: int | None = None
    verdict: str | None = None
    summary: str | None = None
    matched_skills: list[str] | None = None
    missing_skills: list[str] | None = None
    recommendations: list[str] | None = None
    matched_keywords: list[str] | None = None
    missing_keywords: list[str] | None = None
    favorite: bool | None = None
    status: str | None = None
    notes: str | None = None
    tags: list[str] | None = None


def normalize_json_list(value: object) -> str:
    if value is None:
        return "[]"

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return json.dumps(parsed)
        except Exception:
            return json.dumps([item.strip() for item in value.split(",") if item.strip()])

    if isinstance(value, list):
        return json.dumps([str(item).strip() for item in value if str(item).strip()])

    return "[]"


def recruiter_candidate_to_dict(candidate: RecruiterCandidate) -> dict:
    return {
        "id": candidate.id,
        "user_id": candidate.user_id,
        "filename": candidate.filename,
        "cv_storage_path": candidate.cv_storage_path,
        "job_description": candidate.job_description,
        "rank": candidate.rank,
        "score": candidate.score,
        "match_score": candidate.match_score,
        "combined_score": candidate.combined_score,
        "semantic_score": candidate.semantic_score,
        "keyword_score": candidate.keyword_score,
        "verdict": candidate.verdict,
        "summary": candidate.summary,
        "matched_skills": parse_json_list(candidate.matched_skills),
        "missing_skills": parse_json_list(candidate.missing_skills),
        "recommendations": parse_json_list(candidate.recommendations),
        "matched_keywords": parse_json_list(candidate.matched_keywords),
        "missing_keywords": parse_json_list(candidate.missing_keywords),
        "favorite": bool(candidate.favorite),
        "status": candidate.status,
        "notes": candidate.notes,
        "tags": parse_json_list(candidate.tags),
        "source": candidate.source,
        "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
        "updated_at": candidate.updated_at.isoformat() if candidate.updated_at else None,
    }


def normalize_history_score(value: object) -> int:
    """Return a finite, bounded integer score suitable for history records."""
    try:
        if value is None:
            return 0

        if isinstance(value, bool):
            numeric = float(value)
        elif isinstance(value, (int, float)):
            numeric = float(value)
        elif isinstance(value, str):
            match = re.search(r"-?\d+(?:[.,]\d+)?", value)
            if match is None:
                return 0
            numeric = float(match.group(0).replace(",", "."))
        else:
            return 0

        if not math.isfinite(numeric):
            return 0

        if 0 < numeric <= 1:
            numeric *= 100

        return max(0, min(100, int(round(numeric))))
    except (TypeError, ValueError, OverflowError):
        return 0


def normalize_history_list(value: object, *, maximum_items: int = 50) -> list[str]:
    """Normalize bounded string lists before serializing them to the database."""
    if value is None:
        return []

    if isinstance(value, str):
        raw_value = value.strip()
        if not raw_value:
            return []
        try:
            parsed = json.loads(raw_value)
            value = parsed if isinstance(parsed, list) else [raw_value]
        except json.JSONDecodeError:
            value = [item.strip() for item in raw_value.replace("\n", ",").split(",")]

    if not isinstance(value, (list, tuple, set)):
        value = [value]

    normalized: list[str] = []
    seen: set[str] = set()

    for item in value:
        if isinstance(item, (dict, list, tuple, set)):
            continue

        cleaned = re.sub(r"\s+", " ", str(item or "")).strip()
        if not cleaned:
            continue

        cleaned = cleaned[:1000]
        dedupe_key = cleaned.casefold()
        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        normalized.append(cleaned)

        if len(normalized) >= maximum_items:
            break

    return normalized


def first_nonempty_history_list(*values: object) -> list[str]:
    """Return the first candidate value that normalizes to a non-empty list."""
    for value in values:
        normalized = normalize_history_list(value)
        if normalized:
            return normalized
    return []


def first_nonempty_text(*values: object, maximum_length: int = 12000) -> str:
    """Return the first non-empty normalized text value."""
    for value in values:
        normalized = re.sub(r"\s+", " ", str(value or "")).strip()
        if normalized:
            return normalized[:maximum_length]
    return ""


def parse_stored_history_list(value: object) -> list[str]:
    """Safely decode current and legacy history list storage formats."""
    return normalize_history_list(value)


def create_analysis_history_record(
    db: Session,
    current_user: User,
    *,
    analysis_type: str,
    cv_filename: str | None,
    pdf_bytes: bytes | None,
    job_description: str,
    score: int,
    summary: str,
    matched_skills: list[str] | None = None,
    missing_skills: list[str] | None = None,
    recommendations: list[str] | None = None,
) -> AnalysisRecord:
    """Persist a normalized, backward-compatible TalentMatch history record."""
    storage_path = None
    safe_filename = re.sub(
        r"[^A-Za-z0-9._ -]+",
        "_",
        str(cv_filename or "resume.pdf"),
    ).strip()[:255] or "resume.pdf"

    if pdf_bytes:
        try:
            storage_path = upload_pdf_to_firebase(
                pdf_bytes,
                current_user.id,
                safe_filename,
            )
        except Exception:
            logger.exception(
                "Firebase Storage upload failed while saving history.",
                extra={
                    "event": "history_storage_upload_failed",
                    "user_id": current_user.id,
                    "operation": analysis_type,
                },
            )

    normalized_type = str(analysis_type or "cv_analysis").strip().lower()[:50]
    normalized_summary = re.sub(r"\s+", " ", str(summary or "")).strip()[:12000]
    normalized_job_description = str(job_description or "").strip()[:30000]

    record_kwargs = {
        "user_id": current_user.id,
        "cv_filename": safe_filename,
        "cv_storage_path": storage_path,
        "job_description": normalized_job_description,
        "score": normalize_history_score(score),
        "summary": normalized_summary,
        "matched_skills": json.dumps(
            normalize_history_list(matched_skills),
            ensure_ascii=False,
        ),
        "missing_skills": json.dumps(
            normalize_history_list(missing_skills),
            ensure_ascii=False,
        ),
        "recommendations": json.dumps(
            normalize_history_list(recommendations),
            ensure_ascii=False,
        ),
    }

    if hasattr(AnalysisRecord, "analysis_type"):
        record_kwargs["analysis_type"] = normalized_type

    record = AnalysisRecord(**record_kwargs)

    try:
        db.add(record)
        db.commit()
        db.refresh(record)
    except Exception:
        db.rollback()
        logger.exception(
            "History record persistence failed.",
            extra={
                "event": "history_record_persistence_failed",
                "user_id": current_user.id,
                "operation": normalized_type,
            },
        )
        raise

    return record


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "TalentMatch Pro backend running.",
        **config_status(),
    }


@app.get("/robots.txt", include_in_schema=False)
def robots_txt():
    robots_file = STATIC_DIR / "robots.txt"

    if not robots_file.exists():
        raise HTTPException(status_code=404, detail="robots.txt not found.")

    return FileResponse(
        path=str(robots_file),
        media_type="text/plain; charset=utf-8",
    )


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap_xml():
    sitemap_file = STATIC_DIR / "sitemap.xml"

    if not sitemap_file.exists():
        raise HTTPException(status_code=404, detail="sitemap.xml not found.")

    return FileResponse(
        path=str(sitemap_file),
        media_type="application/xml; charset=utf-8",
    )


@app.get("/healthz")
def healthz():
    metrics = METRICS.snapshot(environment=get_environment())
    return {
        "status": "ok",
        "uptime_seconds": metrics["uptime_seconds"],
        "requests_total": metrics["requests_total"],
    }


@app.get("/metrics", include_in_schema=False)
def metrics():
    database_status = get_database_reliability_status()
    pool_status = get_database_pool_status()

    metrics_snapshot = METRICS.snapshot(
        environment=get_environment(),
        database_ok=bool(database_status["connection_ok"]),
    )
    resilience_status = get_resilience_status()

    return {
        **metrics_snapshot,
        "api_reliability_enabled": True,
        "external_services_available": resilience_is_available(
            resilience_status
        ),
        "external_service_circuits": resilience_status,
        "database_connection_ok": database_status["connection_ok"],
        "database_dialect": database_status["dialect"],
        "database_driver": database_status["driver"],
        "database_error_type": database_status["error_type"],
        "database_retryable": database_status["retryable"],
        "database_pool_enabled": database_status["pool_enabled"],
        "database_transaction_safety_enabled": database_status[
            "transaction_safety_enabled"
        ],
        "database_timeout_protection_enabled": database_status[
            "timeout_protection_enabled"
        ],
        "database_connect_timeout_seconds": database_status[
            "connect_timeout_seconds"
        ],
        "database_statement_timeout_ms": database_status[
            "statement_timeout_ms"
        ],
        "database_pool_type": pool_status["pool_type"],
        "database_pool_size": pool_status["pool_size"],
        "database_pool_checked_in": pool_status["checked_in"],
        "database_pool_checked_out": pool_status["checked_out"],
        "database_pool_overflow": pool_status["overflow"],
        "database_pool_timeout_seconds": pool_status["timeout_seconds"],
        "database_pool_recycle_seconds": pool_status["recycle_seconds"],
    }


@app.get("/error-test", include_in_schema=False)
def error_test():
    if get_environment() in {"production", "prod"}:
        raise HTTPException(status_code=404, detail="Not found.")

    raise RuntimeError("Controlled development exception test.")


@app.get("/readyz")
def readyz():
    checks = config_status()
    database_status = get_database_reliability_status()

    checks.update(
        {
            "database_connection_ok": database_status["connection_ok"],
            "database_dialect": database_status["dialect"],
            "database_driver": database_status["driver"],
            "database_error_type": database_status["error_type"],
            "database_retryable": database_status["retryable"],
            "database_pool_enabled": database_status["pool_enabled"],
            "database_transaction_safety_enabled": database_status[
                "transaction_safety_enabled"
            ],
            "database_timeout_protection_enabled": database_status[
                "timeout_protection_enabled"
            ],
            "database_connect_timeout_seconds": database_status[
                "connect_timeout_seconds"
            ],
            "database_statement_timeout_ms": database_status[
                "statement_timeout_ms"
            ],
        }
    )

    if database_status["connection_ok"]:
        return {"status": "ready", **checks}

    return JSONResponse(
        status_code=503,
        content={"status": "not_ready", **checks},
    )


@app.get("/me")
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.expire_all()
    user = db.query(User).filter(User.id == current_user.id).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    usage = get_user_usage(db, user)

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "plan": user.plan,
        "is_pro": bool(user.is_pro),
        "paypal_customer_id": getattr(user, "paypal_customer_id", None),
        "paypal_subscription_id": getattr(user, "paypal_subscription_id", None),
        "paypal_subscription_status": getattr(user, "paypal_subscription_status", None),
        **usage,
    }


@app.post("/analyze-resume", response_model=AnalysisResponse)
async def analyze_resume(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_analysis_allowed(db, current_user)

    pdf_bytes = await file.read()

    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")

    try:
        cv_text = extract_text_from_pdf(pdf_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not extract text from PDF: {exc}")

    if not cv_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from PDF.")

    result = None
    try:
        result = analyze_cv_with_ai(cv_text, job_description)
    except AIServiceError as exc:
        logger.warning("OpenAI CV analysis failed: %s", exc)
        raise_ai_http_exception(exc)

    if result is None:
        raise HTTPException(status_code=502, detail="AI analysis returned no result.")

    create_analysis_history_record(
        db,
        current_user,
        analysis_type="cv_analysis",
        cv_filename=file.filename,
        pdf_bytes=pdf_bytes,
        job_description=job_description,
        score=result["score"],
        summary=result["summary"],
        matched_skills=result["strengths"],
        missing_skills=result["weaknesses"],
        recommendations=result["recommendations"],
    )

    get_user_usage(db, current_user)

    return result


@app.post("/analyze-test", response_model=AnalysisResponse)
async def analyze_test(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    current_user: User = Depends(get_test_user),
):
    pdf_bytes = await file.read()

    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")

    try:
        cv_text = extract_text_from_pdf(pdf_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not extract text from PDF: {exc}")

    if not cv_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from PDF.")

    try:
        return analyze_cv_with_ai(cv_text, job_description)
    except AIServiceError as exc:
        logger.warning("OpenAI analysis test failed: %s", exc)
        raise_ai_http_exception(exc)


ATS_STOPWORDS = {
    "and", "or", "the", "a", "an", "to", "of", "for", "in", "on", "with",
    "as", "is", "are", "be", "by", "this", "that", "you", "your", "we",
    "our", "will", "from", "at", "it", "their", "they", "them",
    "role", "candidate", "candidates", "experience", "skills",
    "strong", "work", "working", "build", "building", "product",
    "products", "what", "have", "has", "about", "into", "against",
    "real", "helps", "using", "job", "jobs", "description",
    "descriptions", "identify", "compare", "platform",
    "founding", "full", "stack", "fullstack", "full-stack",
    "pro", "seekers", "team", "looking", "years", "required",
    "preferred", "talentmatch", "cv", "resume", "engineer",
    "modern", "increase", "chances", "optimize", "powered",
    "analysis", "application", "strategy", "ship", "own", "gaps",
    "improve", "scale", "integrate", "integration", "integrations",
    "workflow", "workflows", "seeker", "company", "companies",
    "startup", "startups", "founder", "owning", "shipping",
    "improving", "scaling", "good", "great", "excellent",
    "need", "needs", "needed", "want", "wants", "ability",
    "able", "must", "should", "could", "would", "high", "value",
    "plus", "bonus", "fast", "paced", "environment",
}


def extract_ats_keywords(text_value: str, limit: int = 30) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{2,}", text_value.lower())
    keywords = []

    for word in words:
        clean = word.strip(".,:;()[]{}")
        if clean and clean not in ATS_STOPWORDS and clean not in keywords:
            keywords.append(clean)

    priority_terms = [
        "python", "fastapi", "sql", "postgresql", "api", "apis", "docker",
        "firebase", "openai", "saas", "backend", "frontend", "streamlit",
        "auth", "authentication", "storage", "billing", "deployment",
        "cloud", "pdf", "ai", "prompt", "database", "render", "mvp",
        "ats", "recruiter", "paypal", "postgres",
        "javascript", "typescript", "react", "rest",
    ]

    ordered = []

    for term in priority_terms:
        if term in keywords and term not in ordered:
            ordered.append(term)

    for keyword in keywords:
        if keyword not in ordered:
            ordered.append(keyword)

    return ordered[:limit]


@app.post("/ats-test")
async def ats_test(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pdf_bytes = await file.read()

    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")

    try:
        cv_text = extract_text_from_pdf(pdf_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not extract text from PDF: {exc}")

    if not cv_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from PDF.")

    keywords = extract_ats_keywords(job_description)
    cv_lower = cv_text.lower()

    matched = []
    missing = []

    for keyword in keywords:
        if keyword.lower() in cv_lower:
            matched.append(keyword)
        else:
            missing.append(keyword)

    coverage = round((len(matched) / len(keywords)) * 100) if keywords else 0
    verdict = "ATS Strong" if coverage >= 80 else "ATS Good" if coverage >= 60 else "ATS Weak"

    recommendations = [
        f"Add missing high-value keywords where truthful: {', '.join(missing[:8])}."
        if missing
        else "Your CV covers the main ATS keywords well.",
        "Mirror important job-description terms naturally in your CV summary and experience bullets.",
        "Use exact tool names where relevant, for example FastAPI, Docker, SQL, Firebase, OpenAI.",
    ]

    result = {
        "score": coverage,
        "coverage": coverage,
        "verdict": verdict,
        "total_keywords": len(keywords),
        "matched_keywords": matched,
        "missing_keywords": missing,
        "recommendations": recommendations,
    }

    create_analysis_history_record(
        db,
        current_user,
        analysis_type="ats_checker",
        cv_filename=file.filename,
        pdf_bytes=pdf_bytes,
        job_description=job_description,
        score=coverage,
        summary=f"ATS keyword check completed. Coverage: {coverage}%. Verdict: {verdict}.",
        matched_skills=matched,
        missing_skills=missing,
        recommendations=recommendations,
    )

    return result


@app.post("/ats-check")
async def ats_check(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pdf_bytes = await file.read()

    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")

    try:
        cv_text = extract_text_from_pdf(pdf_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not extract text from PDF: {exc}")

    if not cv_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from PDF.")

    keywords = extract_ats_keywords(job_description)
    cv_lower = cv_text.lower()

    matched = []
    missing = []

    for keyword in keywords:
        if keyword.lower() in cv_lower:
            matched.append(keyword)
        else:
            missing.append(keyword)

    coverage = round((len(matched) / len(keywords)) * 100) if keywords else 0
    verdict = "ATS Strong" if coverage >= 80 else "ATS Good" if coverage >= 60 else "ATS Weak"

    recommendations = [
        f"Add missing high-value keywords where truthful: {', '.join(missing[:8])}."
        if missing
        else "Your CV covers the main ATS keywords well.",
        "Mirror important job-description terms naturally in your CV summary and experience bullets.",
        "Use exact tool names where relevant, for example FastAPI, Docker, SQL, Firebase, OpenAI.",
    ]

    result = {
        "score": coverage,
        "coverage": coverage,
        "verdict": verdict,
        "total_keywords": len(keywords),
        "matched_keywords": matched,
        "missing_keywords": missing,
        "recommendations": recommendations,
    }

    create_analysis_history_record(
        db,
        current_user,
        analysis_type="ats_checker",
        cv_filename=file.filename,
        pdf_bytes=pdf_bytes,
        job_description=job_description,
        score=coverage,
        summary=f"ATS keyword check completed. Coverage: {coverage}%. Verdict: {verdict}.",
        matched_skills=matched,
        missing_skills=missing,
        recommendations=recommendations,
    )

    return result


@app.post("/semantic-match")
async def semantic_match(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_pro:
        raise HTTPException(status_code=403, detail="Semantic matching is a Pro feature.")

    pdf_bytes = await file.read()

    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")

    try:
        cv_text = extract_text_from_pdf(pdf_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not extract text from PDF: {exc}")

    if not cv_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from PDF.")

    try:
        result = analyze_semantic_match(cv_text, job_description)
    except AIServiceError as exc:
        logger.warning("Semantic Match AI request failed: %s", exc)
        raise_ai_http_exception(exc)
    except Exception:
        logger.exception(
            "Semantic Match processing failed.",
            extra={
                "event": "semantic_match_processing_failed",
                "user_id": current_user.id,
                "operation": "semantic_match",
            },
        )
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Semantic Match could not be completed.",
                "type": "semantic_match_processing_error",
            },
        )

    combined_score = normalize_history_score(
        result.get(
            "combined_score",
            result.get(
                "score",
                result.get("match_score", result.get("semantic_score", 0)),
            ),
        )
    )
    matched_themes = result.get(
        "matched_themes",
        result.get("matched_skills", result.get("strengths", [])),
    )
    missing_themes = result.get(
        "missing_themes",
        result.get("missing_skills", result.get("weaknesses", [])),
    )

    create_analysis_history_record(
        db,
        current_user,
        analysis_type="semantic_match",
        cv_filename=file.filename,
        pdf_bytes=pdf_bytes,
        job_description=job_description,
        score=combined_score,
        summary=result.get("summary", "Semantic match analysis completed."),
        matched_skills=matched_themes,
        missing_skills=missing_themes,
        recommendations=result.get("recommendations", []),
    )

    return result



def normalize_candidate_score(value: object) -> int:
    """Return a finite Candidate Database score bounded to the 0-100 range."""
    return normalize_history_score(value)


def normalize_candidate_text(
    value: object,
    *,
    fallback: str = "",
    maximum_length: int,
) -> str:
    """Normalize user-controlled Candidate Database text fields."""
    normalized = re.sub(r"\\s+", " ", str(value or fallback)).strip()
    return normalized[:maximum_length]


def persist_recruiter_candidate(
    payload: CandidateCreateRequest,
    db: Session,
    current_user: User,
) -> dict:
    """Create one candidate idempotently for the authenticated Recruiter Workspace."""
    if not current_user.is_pro:
        raise HTTPException(status_code=403, detail="Candidate Database is a Pro feature.")

    filename = normalize_candidate_text(
        payload.filename,
        fallback="candidate.pdf",
        maximum_length=255,
    ) or "candidate.pdf"
    job_description = normalize_candidate_text(
        payload.job_description,
        maximum_length=30000,
    )

    existing_candidate = (
        db.query(RecruiterCandidate)
        .filter(
            RecruiterCandidate.user_id == current_user.id,
            RecruiterCandidate.filename == filename,
            RecruiterCandidate.job_description == job_description,
        )
        .order_by(RecruiterCandidate.created_at.desc())
        .first()
    )

    if existing_candidate is not None:
        result = recruiter_candidate_to_dict(existing_candidate)
        result["created"] = False
        result["duplicate"] = True
        return result

    candidate = RecruiterCandidate(
        user_id=current_user.id,
        filename=filename,
        cv_storage_path=normalize_candidate_text(
            payload.cv_storage_path,
            maximum_length=500,
        ) or None,
        job_description=job_description,
        rank=max(0, int(payload.rank or 0)),
        score=normalize_candidate_score(
            payload.score or payload.combined_score or payload.match_score
        ),
        match_score=normalize_candidate_score(payload.match_score),
        combined_score=normalize_candidate_score(
            payload.combined_score or payload.score
        ),
        semantic_score=normalize_candidate_score(payload.semantic_score),
        keyword_score=normalize_candidate_score(payload.keyword_score),
        verdict=normalize_candidate_text(payload.verdict, maximum_length=100),
        summary=normalize_candidate_text(payload.summary, maximum_length=12000),
        matched_skills=normalize_json_list(payload.matched_skills),
        missing_skills=normalize_json_list(payload.missing_skills),
        recommendations=normalize_json_list(payload.recommendations),
        matched_keywords=normalize_json_list(payload.matched_keywords),
        missing_keywords=normalize_json_list(payload.missing_keywords),
        favorite=bool(payload.favorite),
        status=normalize_candidate_text(
            payload.status,
            fallback="new",
            maximum_length=50,
        ) or "new",
        notes=normalize_candidate_text(payload.notes, maximum_length=12000),
        tags=normalize_json_list(payload.tags),
        source="recruiter_mode",
    )

    try:
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
    except Exception:
        db.rollback()
        logger.exception(
            "Recruiter candidate persistence failed.",
            extra={
                "event": "recruiter_candidate_persistence_failed",
                "user_id": current_user.id,
                "operation": "create_candidate",
            },
        )
        raise

    result = recruiter_candidate_to_dict(candidate)
    result["created"] = True
    result["duplicate"] = False
    return result


@app.post("/recruiter/candidates")
@app.post("/recruiter/candidates/save", include_in_schema=False)
def save_recruiter_candidate(
    payload: CandidateCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return persist_recruiter_candidate(payload, db, current_user)


@app.get("/recruiter/candidates")
def list_recruiter_candidates(
    search: str | None = None,
    status: str | None = None,
    favorite: bool | None = None,
    min_score: int = 0,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_pro:
        raise HTTPException(status_code=403, detail="Candidate Database is a Pro feature.")

    query = db.query(RecruiterCandidate).filter(RecruiterCandidate.user_id == current_user.id)

    if status:
        query = query.filter(RecruiterCandidate.status == status)

    if favorite is not None:
        query = query.filter(RecruiterCandidate.favorite == favorite)

    if min_score:
        query = query.filter(RecruiterCandidate.score >= int(min_score))

    if search:
        like_value = f"%{search.strip()}%"
        query = query.filter(
            (RecruiterCandidate.filename.ilike(like_value))
            | (RecruiterCandidate.summary.ilike(like_value))
            | (RecruiterCandidate.notes.ilike(like_value))
            | (RecruiterCandidate.tags.ilike(like_value))
        )

    total = query.count()

    candidates = (
        query.order_by(RecruiterCandidate.created_at.desc())
        .offset(max(int(offset), 0))
        .limit(min(max(int(limit), 1), 250))
        .all()
    )

    return {
        "candidates": [recruiter_candidate_to_dict(candidate) for candidate in candidates],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@app.get("/recruiter/candidates/{candidate_id}")
def get_recruiter_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_pro:
        raise HTTPException(status_code=403, detail="Candidate Database is a Pro feature.")

    candidate = (
        db.query(RecruiterCandidate)
        .filter(
            RecruiterCandidate.id == candidate_id,
            RecruiterCandidate.user_id == current_user.id,
        )
        .first()
    )

    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    return recruiter_candidate_to_dict(candidate)


@app.get("/recruiter/candidate/{candidate_id}")
def get_recruiter_candidate_legacy_alias(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_recruiter_candidate(candidate_id, db, current_user)


@app.put("/recruiter/candidates/{candidate_id}")
def update_recruiter_candidate(
    candidate_id: int,
    payload: CandidateUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_pro:
        raise HTTPException(status_code=403, detail="Candidate Database is a Pro feature.")

    candidate = (
        db.query(RecruiterCandidate)
        .filter(
            RecruiterCandidate.id == candidate_id,
            RecruiterCandidate.user_id == current_user.id,
        )
        .first()
    )

    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    scalar_fields = [
        "filename",
        "cv_storage_path",
        "job_description",
        "rank",
        "score",
        "match_score",
        "combined_score",
        "semantic_score",
        "keyword_score",
        "verdict",
        "summary",
        "favorite",
        "status",
        "notes",
    ]

    updates = payload.model_dump(exclude_unset=True)

    for field_name in scalar_fields:
        if field_name in updates:
            setattr(candidate, field_name, updates[field_name])

    json_fields = [
        "matched_skills",
        "missing_skills",
        "recommendations",
        "matched_keywords",
        "missing_keywords",
        "tags",
    ]

    for field_name in json_fields:
        if field_name in updates:
            setattr(candidate, field_name, normalize_json_list(updates[field_name]))

    db.commit()
    db.refresh(candidate)

    return recruiter_candidate_to_dict(candidate)


@app.delete("/recruiter/candidates/{candidate_id}")
def delete_recruiter_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_pro:
        raise HTTPException(status_code=403, detail="Candidate Database is a Pro feature.")

    candidate = (
        db.query(RecruiterCandidate)
        .filter(
            RecruiterCandidate.id == candidate_id,
            RecruiterCandidate.user_id == current_user.id,
        )
        .first()
    )

    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    db.delete(candidate)
    db.commit()

    return {"status": "deleted", "id": candidate_id}


@app.delete("/recruiter/candidate/{candidate_id}")
def delete_recruiter_candidate_legacy_alias(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return delete_recruiter_candidate(candidate_id, db, current_user)




@app.post(
    "/recruiter/jobs",
    response_model=RecruiterJobCreateResponse,
    status_code=202,
)
async def create_recruiter_job(
    files: list[UploadFile] = File(...),
    job_description: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_pro:
        raise HTTPException(status_code=403, detail="Recruiter Mode is a Pro feature.")

    recruiter_max_candidates = get_positive_int_env("RECRUITER_MAX_CANDIDATES", 100)
    if not files:
        raise HTTPException(status_code=400, detail="Please upload at least one CV.")
    if len(files) > recruiter_max_candidates:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {recruiter_max_candidates} CV files allowed per ranking run.",
        )

    normalized_job_description = str(job_description or "").strip()
    if not normalized_job_description:
        raise HTTPException(status_code=400, detail="Please provide a job description.")

    candidates: list[dict[str, str]] = []
    first_pdf_bytes: bytes | None = None
    first_filename = "candidate.pdf"

    for uploaded_file in files:
        pdf_bytes = await uploaded_file.read()
        filename = uploaded_file.filename or "candidate.pdf"
        if first_pdf_bytes is None and pdf_bytes:
            first_pdf_bytes = pdf_bytes
            first_filename = filename
        try:
            cv_text = extract_text_from_pdf(pdf_bytes) if pdf_bytes else ""
        except Exception as exc:
            logger.warning("CV text extraction failed for %s: %s", filename, exc)
            cv_text = ""
        candidates.append({"filename": filename, "cv_text": cv_text})

    job_id = str(uuid.uuid4())
    input_payload = {
        "candidates": candidates,
        "first_filename": first_filename,
        "first_pdf_base64": (
            base64.b64encode(first_pdf_bytes).decode("ascii")
            if first_pdf_bytes
            else None
        ),
    }
    job = RecruiterJob(
        job_id=job_id,
        user_id=current_user.id,
        status="queued",
        progress=0,
        total_candidates=len(candidates),
        processed_candidates=0,
        job_description=normalized_job_description[:30000],
        input_payload=json.dumps(input_payload, ensure_ascii=False),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    submit_recruiter_job(job.job_id)
    return recruiter_job_to_dict(job, include_result=False)


@app.get(
    "/recruiter/jobs/{job_id}",
    response_model=RecruiterJobStatusResponse,
)
def get_recruiter_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_pro:
        raise HTTPException(status_code=403, detail="Recruiter Mode is a Pro feature.")
    job = (
        db.query(RecruiterJob)
        .filter(RecruiterJob.job_id == job_id, RecruiterJob.user_id == current_user.id)
        .first()
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Recruiter job not found.")
    return recruiter_job_to_dict(job)


@app.post("/recruiter/rank-candidates")
async def recruiter_rank_candidates_legacy(
    files: list[UploadFile] = File(...),
    job_description: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Backward-compatible synchronous endpoint for small existing clients."""
    if len(files) > 10:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Large recruiter batches must use the asynchronous /recruiter/jobs endpoint.",
                "type": "recruiter_async_required",
            },
        )
    if not current_user.is_pro:
        raise HTTPException(status_code=403, detail="Recruiter Mode is a Pro feature.")
    candidates = []
    first_pdf_bytes = None
    first_filename = None
    for uploaded_file in files:
        pdf_bytes = await uploaded_file.read()
        if first_pdf_bytes is None and pdf_bytes:
            first_pdf_bytes = pdf_bytes
            first_filename = uploaded_file.filename or "candidate.pdf"
        cv_text = extract_text_from_pdf(pdf_bytes) if pdf_bytes else ""
        candidates.append({"filename": uploaded_file.filename or "candidate.pdf", "cv_text": cv_text})
    result = rank_candidates(candidates=candidates, job_description=job_description)
    ranked_candidates = result.get("candidates", [])
    top_candidate = ranked_candidates[0] if ranked_candidates else {}
    top_filename = top_candidate.get("filename", first_filename or "candidate.pdf")
    create_analysis_history_record(
        db, current_user, analysis_type="recruiter_mode",
        cv_filename=top_filename, pdf_bytes=first_pdf_bytes,
        job_description=job_description, score=top_candidate.get("score", result.get("score", 0)),
        summary=first_nonempty_text(
            top_candidate.get("summary"),
            result.get("summary"),
            "Recruiter ranking completed.",
        ),
        matched_skills=first_nonempty_history_list(
            top_candidate.get("matched_skills"),
            top_candidate.get("strengths"),
            result.get("matched_skills"),
            result.get("strengths"),
        ),
        missing_skills=first_nonempty_history_list(
            top_candidate.get("missing_skills"),
            top_candidate.get("weaknesses"),
            result.get("missing_skills"),
            result.get("weaknesses"),
        ),
        recommendations=first_nonempty_history_list(
            top_candidate.get("recommendations"),
            result.get("recommendations"),
        ),
    )
    return result


@app.post("/rewrite-cv")
async def rewrite_cv(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_pro:
        raise HTTPException(status_code=403, detail="CV Rewrite AI is a Pro feature.")

    pdf_bytes = await file.read()

    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")

    try:
        cv_text = extract_text_from_pdf(pdf_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not extract text from PDF: {exc}")

    if not cv_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from PDF.")

    try:
        result = rewrite_cv_with_ai(cv_text, job_description)
    except AIServiceError as exc:
        logger.warning("OpenAI CV rewrite failed: %s", exc)
        raise_ai_http_exception(exc)

    create_analysis_history_record(
        db,
        current_user,
        analysis_type="cv_rewrite",
        cv_filename=file.filename,
        pdf_bytes=pdf_bytes,
        job_description=job_description,
        score=100,
        summary="CV Rewrite completed successfully.",
        matched_skills=[],
        missing_skills=[],
        recommendations=[
            "Review the rewritten CV before sending it to employers.",
            "Keep all claims accurate and truthful.",
            "Tailor the final version to the exact job description.",
        ],
    )

    return result


@app.post("/reports/analysis-pdf")
async def create_analysis_pdf_report(
    cv_filename: str = Form(...),
    score: int = Form(...),
    summary: str = Form(...),
    strengths_json: str = Form("[]"),
    weaknesses_json: str = Form("[]"),
    recommendations_json: str = Form("[]"),
    job_description: str = Form(""),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_pro:
        raise HTTPException(status_code=403, detail="PDF reports are a Pro feature.")

    try:
        pdf_bytes = build_analysis_pdf_report(
            cv_filename=cv_filename,
            score=score,
            summary=summary,
            strengths=parse_json_list(strengths_json),
            weaknesses=parse_json_list(weaknesses_json),
            recommendations=parse_json_list(recommendations_json),
            job_description=job_description,
        )
    except Exception as exc:
        logger.exception("PDF report generation failed.")
        raise HTTPException(status_code=500, detail=f"PDF report failed: {exc}")

    safe_filename = re.sub(r"[^a-zA-Z0-9_-]+", "_", cv_filename.replace(".pdf", ""))
    download_name = f"{safe_filename}_talentmatch_report.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
    )


@app.get("/history")
def get_history(
    analysis_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(AnalysisRecord).filter(AnalysisRecord.user_id == current_user.id)

    if analysis_type and hasattr(AnalysisRecord, "analysis_type"):
        query = query.filter(AnalysisRecord.analysis_type == analysis_type)

    records = query.order_by(AnalysisRecord.created_at.desc()).all()

    return [
        {
            "id": record.id,
            "analysis_type": getattr(record, "analysis_type", "cv_analysis") or "cv_analysis",
            "cv_filename": record.cv_filename,
            "cv_storage_path": record.cv_storage_path,
            "job_description": record.job_description,
            "score": record.score,
            "summary": record.summary,
            "matched_skills": parse_stored_history_list(record.matched_skills),
            "missing_skills": parse_stored_history_list(record.missing_skills),
            "recommendations": parse_stored_history_list(record.recommendations),
            "created_at": record.created_at,
        }
        for record in records
    ]


@app.delete("/history/{record_id}")
def delete_history_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = (
        db.query(AnalysisRecord)
        .filter(
            AnalysisRecord.id == record_id,
            AnalysisRecord.user_id == current_user.id,
        )
        .first()
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="History record not found.",
        )

    db.delete(record)
    db.commit()

    get_user_usage(db, current_user)

    return {
        "success": True,
        "message": "History record deleted.",
        "deleted_id": record_id,
    }


@app.delete("/history")
def delete_all_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.user_id == current_user.id)
        .delete(synchronize_session=False)
    )

    db.commit()

    get_user_usage(db, current_user)

    return {
        "success": True,
        "deleted": deleted,
        "message": f"{deleted} history record(s) deleted.",
    }


@app.get("/history-test")
def get_history_test():
    return [
        {
            "id": 1,
            "cv_filename": "demo_cv.pdf",
            "cv_storage_path": None,
            "job_description": "Founding Full-Stack AI SaaS Engineer",
            "score": 75,
            "summary": "Demo analysis history item.",
            "matched_skills": ["Python", "FastAPI", "APIs"],
            "missing_skills": ["PayPal", "PostgreSQL production migrations"],
            "recommendations": ["Add SaaS billing experience.", "Highlight deployment experience."],
            "created_at": "2026-05-29T12:00:00",
        }
    ]


@app.post("/billing/create-checkout")
def create_checkout(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info("PayPal checkout requested.", extra={"event": "paypal_checkout_requested"})
    logger.info("PayPal checkout user resolved.", extra={"event": "paypal_checkout_user_resolved"})
    # Email intentionally not logged to reduce exposure of personal data.

    db.expire_all()
    user = db.query(User).filter(User.id == current_user.id).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    provider = get_billing_provider()
    checkout_url = provider.create_checkout_url(user)

    logger.info("PayPal checkout URL created.", extra={"event": "paypal_checkout_created"})

    return {"checkout_url": checkout_url}


@app.post("/billing/create-portal")
def create_portal(current_user: User = Depends(get_current_user)):
    provider = get_billing_provider()
    return {"portal_url": provider.create_customer_portal_url(current_user)}


@app.post("/billing/demo-upgrade")
def demo_upgrade_to_pro(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.plan = "pro"
    current_user.is_pro = True
    if hasattr(current_user, "paypal_subscription_status"):
        current_user.paypal_subscription_status = "demo_pro"

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return {
        "status": "ok",
        "message": "Demo upgrade successful.",
        "plan": current_user.plan,
        "is_pro": bool(current_user.is_pro),
    }


@app.post("/billing/webhook")
async def billing_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    body = await request.body()
    provider = get_billing_provider()
    return provider.handle_webhook(body=body, headers=dict(request.headers), db=db)


@app.post("/paypal/webhook")
async def paypal_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    body = await request.body()
    provider = get_billing_provider()
    return provider.handle_webhook(body=body, headers=dict(request.headers), db=db)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "10000"))

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )