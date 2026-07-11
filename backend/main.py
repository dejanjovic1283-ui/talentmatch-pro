import asyncio
import json
import logging
import os
import re
import ssl
import sys
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import NoReturn

import certifi
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
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


from auth import get_current_user, get_test_user
from billing.factory import get_billing_provider
from db import Base, engine, get_db
from models import AnalysisRecord, RecruiterCandidate, User
from openai_service import AIServiceError, analyze_cv_with_ai, rewrite_cv_with_ai
from pdf_report import build_analysis_pdf_report
from pdf_utils import extract_text_from_pdf
from recruiter_service import rank_candidates
from schemas import AnalysisResponse, HistoryItemResponse
from semantic_service import analyze_semantic_match
from storage import upload_pdf_to_firebase
from usage_service import ensure_analysis_allowed, get_user_usage


Base.metadata.create_all(bind=engine)


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
) -> JSONResponse:
    request_id = request_id_from_state(request)

    content = {
        "detail": detail,
        "error": {
            "type": error_type,
            "message": message,
            "status_code": status_code,
            "request_id": request_id,
        },
    }

    if details is not None:
        content["error"]["details"] = details

    response = JSONResponse(
        status_code=status_code,
        content=content,
        headers=headers,
    )
    response.headers["X-Request-ID"] = request_id
    return response


app = FastAPI(title="TalentMatch Pro API", version="0.1.0")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    detail = exc.detail
    message = error_message_from_detail(detail, "The request could not be completed.")

    return build_error_response(
        request=request,
        status_code=exc.status_code,
        error_type="http_error",
        message=message,
        detail=detail,
        headers=dict(exc.headers or {}),
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


def config_status() -> dict:
    database_url = os.getenv("DATABASE_URL", "").strip()
    firebase_credentials = os.getenv("FIREBASE_CREDENTIALS", "").strip()
    google_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()

    return {
        "environment": get_environment(),
        "https_redirect_enabled": should_force_https(),
        "hsts_enabled": should_enable_hsts(),
        "security_headers_enabled": True,
        "production_logging_enabled": True,
        "request_id_enabled": True,
        "exception_handling_enabled": True,
        "standard_error_responses_enabled": True,
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
    raise HTTPException(
        status_code=exc.status_code,
        detail={
            "message": exc.message,
            "type": "ai_service_error",
        },
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
    """
    Centralized history writer for:
    - cv_analysis
    - ats_checker
    - semantic_match
    - recruiter_mode
    """

    storage_path = None

    if pdf_bytes:
        try:
            storage_path = upload_pdf_to_firebase(
                pdf_bytes,
                current_user.id,
                cv_filename or "resume.pdf",
            )
        except Exception as exc:
            logger.exception("Firebase Storage upload failed.")
            storage_path = None

    record_kwargs = {
        "user_id": current_user.id,
        "cv_filename": cv_filename or "resume.pdf",
        "cv_storage_path": storage_path,
        "job_description": job_description,
        "score": int(score or 0),
        "summary": summary or "",
        "matched_skills": json.dumps(matched_skills or []),
        "missing_skills": json.dumps(missing_skills or []),
        "recommendations": json.dumps(recommendations or []),
    }

    if hasattr(AnalysisRecord, "analysis_type"):
        record_kwargs["analysis_type"] = analysis_type

    record = AnalysisRecord(**record_kwargs)

    db.add(record)
    db.commit()
    db.refresh(record)

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
    return {"status": "ok"}


@app.get("/error-test", include_in_schema=False)
def error_test():
    if get_environment() in {"production", "prod"}:
        raise HTTPException(status_code=404, detail="Not found.")

    raise RuntimeError("Controlled development exception test.")


@app.get("/readyz")
def readyz(db: Session = Depends(get_db)):
    checks = config_status()

    try:
        db.execute(text("SELECT 1"))
        checks["database_connection_ok"] = True
    except Exception:
        checks["database_connection_ok"] = False

    status = "ready" if checks["database_connection_ok"] else "not_ready"
    return {"status": status, **checks}


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
    except Exception as exc:
        logger.exception("Semantic Match processing failed.")
        raise HTTPException(status_code=500, detail=f"Semantic match failed: {exc}")

    create_analysis_history_record(
        db,
        current_user,
        analysis_type="semantic_match",
        cv_filename=file.filename,
        pdf_bytes=pdf_bytes,
        job_description=job_description,
        score=result.get("score", result.get("match_score", 0)),
        summary=result.get("summary", "Semantic match analysis completed."),
        matched_skills=result.get("matched_skills", result.get("strengths", [])),
        missing_skills=result.get("missing_skills", result.get("weaknesses", [])),
        recommendations=result.get("recommendations", []),
    )

    return result



@app.post("/recruiter/candidates/save")
def save_recruiter_candidate(
    payload: CandidateCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_pro:
        raise HTTPException(status_code=403, detail="Candidate Database is a Pro feature.")

    candidate = RecruiterCandidate(
        user_id=current_user.id,
        filename=payload.filename or "candidate.pdf",
        cv_storage_path=payload.cv_storage_path,
        job_description=payload.job_description or "",
        rank=int(payload.rank or 0),
        score=int(payload.score or payload.combined_score or payload.match_score or 0),
        match_score=int(payload.match_score or 0),
        combined_score=int(payload.combined_score or payload.score or 0),
        semantic_score=int(payload.semantic_score or 0),
        keyword_score=int(payload.keyword_score or 0),
        verdict=payload.verdict or "",
        summary=payload.summary or "",
        matched_skills=normalize_json_list(payload.matched_skills),
        missing_skills=normalize_json_list(payload.missing_skills),
        recommendations=normalize_json_list(payload.recommendations),
        matched_keywords=normalize_json_list(payload.matched_keywords),
        missing_keywords=normalize_json_list(payload.missing_keywords),
        favorite=bool(payload.favorite),
        status=payload.status or "new",
        notes=payload.notes or "",
        tags=normalize_json_list(payload.tags),
        source="recruiter_mode",
    )

    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    return recruiter_candidate_to_dict(candidate)


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




@app.post("/recruiter/rank-candidates")
async def recruiter_rank_candidates(
    files: list[UploadFile] = File(...),
    job_description: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_pro:
        raise HTTPException(status_code=403, detail="Recruiter Mode is a Pro feature.")

    if not files:
        raise HTTPException(status_code=400, detail="Please upload at least one CV.")

    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 CV files allowed per ranking run.")

    candidates = []
    first_pdf_bytes = None
    first_filename = None

    for uploaded_file in files:
        pdf_bytes = await uploaded_file.read()

        if first_pdf_bytes is None and pdf_bytes:
            first_pdf_bytes = pdf_bytes
            first_filename = uploaded_file.filename or "candidate.pdf"

        try:
            cv_text = extract_text_from_pdf(pdf_bytes) if pdf_bytes else ""
        except Exception as exc:
            logger.warning("CV text extraction failed for %s: %s", uploaded_file.filename, exc)
            cv_text = ""

        candidates.append(
            {
                "filename": uploaded_file.filename or "candidate.pdf",
                "cv_text": cv_text,
            }
        )

    try:
        result = rank_candidates(candidates=candidates, job_description=job_description)
    except AIServiceError as exc:
        logger.warning("Recruiter AI ranking failed: %s", exc)
        raise_ai_http_exception(exc)
    except Exception as exc:
        logger.exception("Recruiter ranking failed.")
        raise HTTPException(status_code=500, detail=f"Recruiter ranking failed: {exc}")

    ranked_candidates = result.get("candidates", result.get("ranked_candidates", []))
    top_candidate = ranked_candidates[0] if ranked_candidates else {}
    top_filename = top_candidate.get("filename", first_filename or "candidate.pdf")
    top_score = top_candidate.get("score", result.get("score", 0))

    create_analysis_history_record(
        db,
        current_user,
        analysis_type="recruiter_mode",
        cv_filename=top_filename,
        pdf_bytes=first_pdf_bytes,
        job_description=job_description,
        score=top_score,
        summary=result.get(
            "summary",
            f"Recruiter ranking completed for {len(candidates)} candidate(s). Top candidate: {top_filename}.",
        ),
        matched_skills=top_candidate.get("matched_skills", top_candidate.get("strengths", [])),
        missing_skills=top_candidate.get("missing_skills", top_candidate.get("weaknesses", [])),
        recommendations=result.get("recommendations", top_candidate.get("recommendations", [])),
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
            "matched_skills": json.loads(record.matched_skills or "[]"),
            "missing_skills": json.loads(record.missing_skills or "[]"),
            "recommendations": json.loads(record.recommendations or "[]"),
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