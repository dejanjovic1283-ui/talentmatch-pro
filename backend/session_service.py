"""Server-side durable browser sessions backed by Firebase refresh tokens."""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Final
from urllib.parse import urlparse

import requests
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db import rollback_session_safely
from models import PersistentAuthSession, User


LOGGER = logging.getLogger("talentmatch.sessions")

FIREBASE_TOKEN_REFRESH_ENDPOINT: Final[str] = (
    "https://securetoken.googleapis.com/v1/token"
)
PERSISTENT_SESSION_HEADER: Final[str] = "X-TalentMatch-Session"
DEFAULT_COOKIE_NAME: Final[str] = "tm_session"
DEFAULT_SESSION_TTL_SECONDS: Final[int] = 7 * 24 * 60 * 60
DEFAULT_ACTIVATION_TTL_SECONDS: Final[int] = 60
DEFAULT_FIREBASE_TIMEOUT_SECONDS: Final[float] = 30.0


@dataclass(frozen=True)
class SessionCookieSettings:
    """Cookie settings shared by the activation endpoint and the frontend."""

    name: str
    domain: str | None
    secure: bool
    max_age_seconds: int


@dataclass(frozen=True)
class PersistentSessionBootstrap:
    """One-time browser activation data returned after a Firebase login."""

    activation_code: str
    activation_expires_in_seconds: int


@dataclass(frozen=True)
class PersistentSessionActivation:
    """Opaque cookie value issued exactly once to a browser."""

    session_token: str
    max_age_seconds: int


@dataclass(frozen=True)
class PersistentSessionRestore:
    """Fresh Firebase credentials restored from a trusted server-side session."""

    id_token: str
    expires_in_seconds: int
    email: str
    full_name: str


@dataclass(frozen=True)
class FirebaseRefreshResult:
    """Validated response from Firebase Secure Token API."""

    id_token: str
    refresh_token: str
    firebase_uid: str
    expires_in_seconds: int


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""

    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    """Normalize database values from SQLite and PostgreSQL before comparison."""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_production_environment() -> bool:
    environment = os.getenv(
        "ENVIRONMENT",
        os.getenv("APP_ENV", "development"),
    ).strip().lower()
    return environment in {"production", "prod"}


def _env_flag(name: str, default: bool) -> bool:
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


def _bounded_int_env(
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
        raise RuntimeError(f"{name} must be an integer.") from exc

    if value < minimum or value > maximum:
        raise RuntimeError(
            f"{name} must be between {minimum} and {maximum}."
        )
    return value


def _session_error(
    status_code: int,
    error_type: str,
    message: str,
    *,
    retryable: bool = False,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "message": message,
            "type": error_type,
            "service": "Persistent Session",
            "retryable": retryable,
        },
    )


def get_session_cookie_settings() -> SessionCookieSettings:
    """Read and validate the opaque browser cookie configuration."""

    name = os.getenv("AUTH_SESSION_COOKIE_NAME", DEFAULT_COOKIE_NAME).strip()
    if not name or any(character.isspace() for character in name):
        raise RuntimeError("AUTH_SESSION_COOKIE_NAME must be a valid cookie name.")

    configured_domain = os.getenv("AUTH_SESSION_COOKIE_DOMAIN", "").strip()
    if not configured_domain and _is_production_environment():
        configured_domain = ".talentmatchcv.com"

    if configured_domain:
        normalized_domain = configured_domain.lstrip(".").lower()
        if (
            not normalized_domain
            or "/" in normalized_domain
            or ":" in normalized_domain
            or " " in normalized_domain
        ):
            raise RuntimeError(
                "AUTH_SESSION_COOKIE_DOMAIN must contain only a hostname."
            )
        domain: str | None = f".{normalized_domain}"
    else:
        domain = None

    return SessionCookieSettings(
        name=name,
        domain=domain,
        secure=_env_flag(
            "AUTH_SESSION_COOKIE_SECURE",
            default=_is_production_environment(),
        ),
        max_age_seconds=_bounded_int_env(
            "AUTH_SESSION_TTL_SECONDS",
            DEFAULT_SESSION_TTL_SECONDS,
            minimum=60 * 60,
            maximum=31 * 24 * 60 * 60,
        ),
    )


def get_session_activation_ttl_seconds() -> int:
    """Return the short lifespan for a one-time browser activation code."""

    return _bounded_int_env(
        "AUTH_SESSION_ACTIVATION_TTL_SECONDS",
        DEFAULT_ACTIVATION_TTL_SECONDS,
        minimum=30,
        maximum=300,
    )


def get_public_api_url() -> str:
    """Return the browser-reachable backend origin used for activation links."""

    default = (
        "https://api.talentmatchcv.com"
        if _is_production_environment()
        else "http://localhost:8000"
    )
    raw_url = os.getenv("PUBLIC_API_URL", default).strip().rstrip("/")
    parsed = urlparse(raw_url)

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError("PUBLIC_API_URL must be an absolute HTTP(S) URL.")
    if _is_production_environment() and parsed.scheme != "https":
        raise RuntimeError("PUBLIC_API_URL must use HTTPS in production.")

    return raw_url


def get_frontend_url() -> str:
    """Return the fixed, trusted frontend destination after cookie activation."""

    default = (
        "https://talentmatchcv.com"
        if _is_production_environment()
        else "http://localhost:8501"
    )
    raw_url = os.getenv("FRONTEND_URL", default).strip().rstrip("/")
    parsed = urlparse(raw_url)

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError("FRONTEND_URL must be an absolute HTTP(S) URL.")
    if _is_production_environment() and parsed.scheme != "https":
        raise RuntimeError("FRONTEND_URL must use HTTPS in production.")

    return raw_url


def _fernet() -> Fernet:
    """Load the mandatory at-rest encryption key without ever logging it."""

    raw_key = os.getenv("AUTH_SESSION_ENCRYPTION_KEY", "").strip()
    if not raw_key:
        raise _session_error(
            503,
            "persistent_session_not_configured",
            "Secure persistent sessions are not configured. Please sign in again later.",
            retryable=False,
        )

    try:
        return Fernet(raw_key.encode("utf-8"))
    except (TypeError, ValueError) as exc:
        LOGGER.error(
            "Persistent-session encryption key is invalid.",
            extra={"event": "persistent_session_key_invalid"},
        )
        raise _session_error(
            503,
            "persistent_session_not_configured",
            "Secure persistent sessions are not configured. Please sign in again later.",
            retryable=False,
        ) from exc


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _new_secret() -> str:
    """Return a cryptographically random opaque browser/server secret."""

    return secrets.token_urlsafe(32)


def _clean_refresh_token(value: str) -> str:
    token = str(value or "").strip()
    if len(token) < 20 or len(token) > 4096:
        raise _session_error(
            400,
            "invalid_refresh_token",
            "The authentication session could not be established. Please sign in again.",
        )
    return token


def _clean_session_token(value: str | None) -> str:
    token = str(value or "").strip()
    if len(token) < 20 or len(token) > 512:
        raise _session_error(
            401,
            "persistent_session_missing",
            "Your secure session is unavailable. Please sign in again.",
        )
    return token


def _firebase_timeout_seconds() -> float:
    raw_value = os.getenv(
        "FIREBASE_TIMEOUT_SECONDS",
        str(DEFAULT_FIREBASE_TIMEOUT_SECONDS),
    ).strip()
    try:
        timeout = float(raw_value)
    except ValueError:
        return DEFAULT_FIREBASE_TIMEOUT_SECONDS
    return min(max(timeout, 1.0), 300.0)


def _refresh_firebase_credentials(refresh_token: str) -> FirebaseRefreshResult:
    """Exchange a Firebase refresh token without exposing it to the caller."""

    api_key = os.getenv("FIREBASE_API_KEY", "").strip()
    if not api_key:
        raise _session_error(
            503,
            "firebase_configuration_error",
            "Firebase authentication is not configured. Please try again later.",
        )

    try:
        response = requests.post(
            f"{FIREBASE_TOKEN_REFRESH_ENDPOINT}?key={api_key}",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            timeout=_firebase_timeout_seconds(),
        )
    except requests.Timeout as exc:
        raise _session_error(
            503,
            "firebase_refresh_timeout",
            "Firebase session renewal timed out. Please try again.",
            retryable=True,
        ) from exc
    except requests.RequestException as exc:
        raise _session_error(
            503,
            "firebase_refresh_unavailable",
            "Firebase session renewal is temporarily unavailable. Please try again.",
            retryable=True,
        ) from exc

    if response.status_code != 200:
        if response.status_code in {400, 401, 403}:
            raise _session_error(
                401,
                "firebase_refresh_rejected",
                "Your authentication session is no longer valid. Please sign in again.",
            )
        if response.status_code in {408, 425, 429, 500, 502, 503, 504}:
            raise _session_error(
                503,
                "firebase_refresh_unavailable",
                "Firebase session renewal is temporarily unavailable. Please try again.",
                retryable=True,
            )
        raise _session_error(
            502,
            "firebase_refresh_failed",
            "Firebase session renewal failed. Please try again.",
            retryable=True,
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise _session_error(
            502,
            "firebase_refresh_invalid_response",
            "Firebase returned an invalid session response. Please try again.",
            retryable=True,
        ) from exc

    if not isinstance(payload, dict):
        raise _session_error(
            502,
            "firebase_refresh_invalid_response",
            "Firebase returned an invalid session response. Please try again.",
            retryable=True,
        )

    id_token = str(payload.get("id_token") or "").strip()
    new_refresh_token = str(payload.get("refresh_token") or "").strip()
    firebase_uid = str(payload.get("user_id") or "").strip()
    try:
        expires_in_seconds = int(str(payload.get("expires_in") or "0"))
    except ValueError:
        expires_in_seconds = 0

    if (
        not id_token
        or not new_refresh_token
        or not firebase_uid
        or expires_in_seconds <= 0
    ):
        raise _session_error(
            502,
            "firebase_refresh_invalid_response",
            "Firebase returned an incomplete session response. Please try again.",
            retryable=True,
        )

    return FirebaseRefreshResult(
        id_token=id_token,
        refresh_token=new_refresh_token,
        firebase_uid=firebase_uid,
        expires_in_seconds=expires_in_seconds,
    )


def _encrypt_refresh_token(refresh_token: str) -> str:
    return _fernet().encrypt(refresh_token.encode("utf-8")).decode("utf-8")


def _decrypt_refresh_token(encrypted_value: str) -> str:
    try:
        return _fernet().decrypt(encrypted_value.encode("utf-8")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError) as exc:
        raise _session_error(
            401,
            "persistent_session_unusable",
            "Your secure session is no longer valid. Please sign in again.",
        ) from exc


def _commit_or_raise(
    db: Session,
    *,
    event: str,
    message: str,
) -> None:
    try:
        db.commit()
    except SQLAlchemyError as exc:
        rollback_session_safely(db)
        LOGGER.exception(
            message,
            extra={"event": event, "retryable": True},
        )
        raise _session_error(
            503,
            "persistent_session_store_unavailable",
            "Secure session storage is temporarily unavailable. Please try again.",
            retryable=True,
        ) from exc


def _revoke_session_record(
    db: Session,
    session: PersistentAuthSession,
    *,
    now: datetime,
    event: str,
) -> None:
    # Once a session is revoked, neither the browser credential used for
    # activation nor the Firebase refresh credential is needed anymore.  Keep
    # the row for audit/diagnostics, but remove both ciphertexts immediately.
    session.revoked_at = now
    session.activation_code_hash = None
    session.activation_expires_at = None
    session.session_token_encrypted = ""
    session.refresh_token_encrypted = ""
    user_id = session.user_id
    _commit_or_raise(
        db,
        event=event,
        message="Failed to revoke persistent authentication session.",
    )
    LOGGER.info(
        "Persistent authentication session revoked.",
        extra={"event": event, "user_id": user_id},
    )


def _cleanup_expired_sessions(db: Session, *, now: datetime) -> None:
    """Remove sessions whose opaque credential can no longer be valid."""

    try:
        db.query(PersistentAuthSession).filter(
            PersistentAuthSession.expires_at < now
        ).delete(synchronize_session=False)
        db.commit()
    except SQLAlchemyError:
        rollback_session_safely(db)
        LOGGER.warning(
            "Expired persistent-session cleanup was skipped.",
            extra={"event": "persistent_session_cleanup_failed", "retryable": True},
        )


def create_persistent_session(
    db: Session,
    *,
    current_user: User,
    firebase_refresh_token: str,
) -> PersistentSessionBootstrap:
    """Create an encrypted server-side session from a verified Firebase login."""

    refresh_token = _clean_refresh_token(firebase_refresh_token)
    refreshed = _refresh_firebase_credentials(refresh_token)

    if refreshed.firebase_uid != str(current_user.firebase_uid or "").strip():
        raise _session_error(
            403,
            "persistent_session_identity_mismatch",
            "The authentication session does not match this account. Please sign in again.",
        )

    now = utc_now()
    cookie_settings = get_session_cookie_settings()
    activation_ttl_seconds = get_session_activation_ttl_seconds()
    _cleanup_expired_sessions(db, now=now)

    try:
        db.query(PersistentAuthSession).filter(
            PersistentAuthSession.user_id == current_user.id,
            PersistentAuthSession.activated_at.is_(None),
            PersistentAuthSession.revoked_at.is_(None),
        ).update(
            {
                PersistentAuthSession.revoked_at: now,
                PersistentAuthSession.activation_code_hash: None,
                PersistentAuthSession.activation_expires_at: None,
                PersistentAuthSession.session_token_encrypted: "",
                PersistentAuthSession.refresh_token_encrypted: "",
            },
            synchronize_session=False,
        )

        session_token = _new_secret()
        activation_code = _new_secret()
        db.add(
            PersistentAuthSession(
                user_id=current_user.id,
                session_token_hash=_hash_secret(session_token),
                session_token_encrypted=_encrypt_refresh_token(session_token),
                refresh_token_encrypted=_encrypt_refresh_token(
                    refreshed.refresh_token
                ),
                activation_code_hash=_hash_secret(activation_code),
                activation_expires_at=(
                    now + timedelta(seconds=activation_ttl_seconds)
                ),
                expires_at=now + timedelta(seconds=cookie_settings.max_age_seconds),
                last_seen_at=now,
            )
        )
        _commit_or_raise(
            db,
            event="persistent_session_create_failed",
            message="Failed to create persistent authentication session.",
        )
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        rollback_session_safely(db)
        LOGGER.exception(
            "Failed to prepare persistent authentication session.",
            extra={"event": "persistent_session_create_failed", "user_id": current_user.id},
        )
        raise _session_error(
            503,
            "persistent_session_store_unavailable",
            "Secure session storage is temporarily unavailable. Please try again.",
            retryable=True,
        ) from exc

    LOGGER.info(
        "Persistent authentication session created.",
        extra={"event": "persistent_session_created", "user_id": current_user.id},
    )
    return PersistentSessionBootstrap(
        activation_code=activation_code,
        activation_expires_in_seconds=activation_ttl_seconds,
    )


def activate_persistent_session(
    db: Session,
    *,
    activation_code: str,
) -> PersistentSessionActivation:
    """Consume a short-lived code and return the opaque cookie value exactly once."""

    code = _clean_session_token(activation_code)
    now = utc_now()

    try:
        session = (
            db.query(PersistentAuthSession)
            .filter(
                PersistentAuthSession.activation_code_hash == _hash_secret(code),
                PersistentAuthSession.revoked_at.is_(None),
            )
            .with_for_update()
            .first()
        )
    except SQLAlchemyError as exc:
        rollback_session_safely(db)
        raise _session_error(
            503,
            "persistent_session_store_unavailable",
            "Secure session storage is temporarily unavailable. Please try again.",
            retryable=True,
        ) from exc

    if (
        session is None
        or session.activated_at is not None
        or session.activation_expires_at is None
        or _as_utc(session.activation_expires_at) <= now
        or _as_utc(session.expires_at) <= now
    ):
        if session is not None:
            _revoke_session_record(
                db,
                session,
                now=now,
                event="persistent_session_activation_expired",
            )
        raise _session_error(
            401,
            "persistent_session_activation_invalid",
            "This secure sign-in link has expired. Please sign in again.",
        )

    session.activated_at = now
    session.activation_code_hash = None
    session.activation_expires_at = None
    session.last_seen_at = now
    try:
        session_token = _decrypt_refresh_token(session.session_token_encrypted)
    except HTTPException:
        _revoke_session_record(
            db,
            session,
            now=now,
            event="persistent_session_activation_decrypt_failed",
        )
        raise

    if _hash_secret(session_token) != session.session_token_hash:
        _revoke_session_record(
            db,
            session,
            now=now,
            event="persistent_session_activation_token_mismatch",
        )
        raise _session_error(
            401,
            "persistent_session_activation_invalid",
            "This secure sign-in link has expired. Please sign in again.",
        )

    # The opaque session token is now being returned to the browser and its
    # hash is sufficient for future lookups.  Do not retain a second encrypted
    # copy after one-time activation.
    session.session_token_encrypted = ""
    _commit_or_raise(
        db,
        event="persistent_session_activation_failed",
        message="Failed to activate persistent authentication session.",
    )

    max_age_seconds = max(
        1,
        int((_as_utc(session.expires_at) - now).total_seconds()),
    )
    LOGGER.info(
        "Persistent authentication session activated.",
        extra={"event": "persistent_session_activated", "user_id": session.user_id},
    )
    return PersistentSessionActivation(
        session_token=session_token,
        max_age_seconds=max_age_seconds,
    )


def restore_persistent_session(
    db: Session,
    *,
    session_token: str | None,
) -> PersistentSessionRestore:
    """Mint a fresh Firebase ID token from a valid encrypted server session."""

    token = _clean_session_token(session_token)
    now = utc_now()

    try:
        session = (
            db.query(PersistentAuthSession)
            .filter(
                PersistentAuthSession.session_token_hash == _hash_secret(token),
                PersistentAuthSession.revoked_at.is_(None),
            )
            .with_for_update()
            .first()
        )
    except SQLAlchemyError as exc:
        rollback_session_safely(db)
        raise _session_error(
            503,
            "persistent_session_store_unavailable",
            "Secure session storage is temporarily unavailable. Please try again.",
            retryable=True,
        ) from exc

    if (
        session is None
        or session.activated_at is None
        or _as_utc(session.expires_at) <= now
    ):
        if session is not None:
            _revoke_session_record(
                db,
                session,
                now=now,
                event="persistent_session_expired",
            )
        raise _session_error(
            401,
            "persistent_session_invalid",
            "Your secure session has expired. Please sign in again.",
        )

    try:
        refresh_token = _decrypt_refresh_token(session.refresh_token_encrypted)
        refreshed = _refresh_firebase_credentials(refresh_token)
    except HTTPException as exc:
        if exc.status_code in {401, 403}:
            _revoke_session_record(
                db,
                session,
                now=now,
                event="persistent_session_firebase_rejected",
            )
        raise

    if refreshed.firebase_uid != str(session.user.firebase_uid or "").strip():
        _revoke_session_record(
            db,
            session,
            now=now,
            event="persistent_session_identity_mismatch",
        )
        raise _session_error(
            401,
            "persistent_session_identity_mismatch",
            "Your secure session is no longer valid. Please sign in again.",
        )

    session.refresh_token_encrypted = _encrypt_refresh_token(
        refreshed.refresh_token
    )
    # Older rows may still contain this activation-only ciphertext.  Restore
    # never needs it, so clean it opportunistically while the row is locked.
    session.session_token_encrypted = ""
    session.last_seen_at = now
    _commit_or_raise(
        db,
        event="persistent_session_restore_failed",
        message="Failed to renew persistent authentication session.",
    )

    LOGGER.info(
        "Persistent authentication session restored.",
        extra={"event": "persistent_session_restored", "user_id": session.user_id},
    )
    return PersistentSessionRestore(
        id_token=refreshed.id_token,
        expires_in_seconds=refreshed.expires_in_seconds,
        email=str(session.user.email or "").strip().lower(),
        full_name=str(session.user.full_name or "").strip(),
    )


def revoke_persistent_session(
    db: Session,
    *,
    session_token: str | None,
) -> None:
    """Invalidate a browser's opaque session token without revealing its status."""

    try:
        token = _clean_session_token(session_token)
    except HTTPException:
        return

    try:
        session = (
            db.query(PersistentAuthSession)
            .filter(
                PersistentAuthSession.session_token_hash == _hash_secret(token),
                PersistentAuthSession.revoked_at.is_(None),
            )
            .with_for_update()
            .first()
        )
    except SQLAlchemyError as exc:
        rollback_session_safely(db)
        LOGGER.exception(
            "Persistent-session revocation could not query the database.",
            extra={"event": "persistent_session_revoke_lookup_failed", "retryable": True},
        )
        raise _session_error(
            503,
            "persistent_session_store_unavailable",
            "Secure session storage is temporarily unavailable. Please try again.",
            retryable=True,
        ) from exc

    if session is None:
        return

    _revoke_session_record(
        db,
        session,
        now=utc_now(),
        event="persistent_session_revoke_failed",
    )
