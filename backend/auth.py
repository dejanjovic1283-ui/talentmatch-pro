from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Callable, TypeVar

import requests
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from db import get_db
from models import User
from resilience import (
    CircuitBreakerOpenError,
    ExternalServiceError,
    ExternalServiceTimeoutError,
    ExternalServiceUnavailableError,
    build_resilience_executor,
    get_float_setting,
)


T = TypeVar("T")

LOGGER = logging.getLogger("talentmatch.firebase")

FIREBASE_SERVICE_NAME = "Firebase Authentication"
FIREBASE_CONFIGURATION_PREFIX = "FIREBASE"

bearer_scheme = HTTPBearer(auto_error=False)

FIREBASE_RESILIENCE = build_resilience_executor(
    service=FIREBASE_SERVICE_NAME,
    prefix=FIREBASE_CONFIGURATION_PREFIX,
    logger=LOGGER,
)


class FirebaseServiceError(ExternalServiceError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 503,
        error_code: str = "firebase_service_error",
        retryable: bool = False,
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(
            service=FIREBASE_SERVICE_NAME,
            message=message,
            error_code=error_code,
            status_code=status_code,
            retryable=retryable,
            retry_after_seconds=retry_after_seconds,
        )


def get_firebase_timeout_seconds() -> float:
    return get_float_setting(
        "FIREBASE_TIMEOUT_SECONDS",
        30.0,
        minimum=1.0,
        maximum=300.0,
    )


def _clean_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def _clean_display_name(value: Any) -> str:
    raw = _clean_text(value)
    if not raw:
        return ""

    if "@" in raw:
        raw = raw.split("@", 1)[0]

    raw = raw.replace(".", " ").replace("_", " ").replace("-", " ")
    raw = re.sub(r"[0-9]+", "", raw)
    raw = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()

    if not raw:
        return ""

    parts = [part for part in raw.split() if part]
    display_name = " ".join(
        part[:1].upper() + part[1:].lower()
        for part in parts[:3]
    )

    compact = re.sub(r"[^a-zA-Z]", "", display_name).lower()
    if "dejan" in compact and "jovic" in compact:
        return "Dejan Jovic"

    return display_name


def _name_from_email(email: str) -> str:
    return _clean_display_name(email) or "TalentMatch User"


def _firebase_display_name(
    firebase_user: dict[str, Any],
    email: str,
) -> str:
    direct_name = _clean_display_name(
        firebase_user.get("displayName")
    )
    if direct_name:
        return direct_name

    providers = firebase_user.get("providerUserInfo") or []

    if isinstance(providers, list):
        for provider in providers:
            if not isinstance(provider, dict):
                continue

            provider_name = _clean_display_name(
                provider.get("displayName")
            )
            if provider_name:
                return provider_name

    return _name_from_email(email)


def _is_retryable_firebase_error(exc: Exception) -> bool:
    if isinstance(
        exc,
        (
            requests.ConnectTimeout,
            requests.ReadTimeout,
            requests.ConnectionError,
        ),
    ):
        return True

    if isinstance(exc, requests.HTTPError):
        response = exc.response
        if response is None:
            return False

        return response.status_code in {
            408,
            409,
            429,
            500,
            502,
            503,
            504,
        }

    return False


def _translate_firebase_error(
    exc: Exception,
) -> ExternalServiceError:
    if isinstance(exc, FirebaseServiceError):
        return exc

    if isinstance(exc, CircuitBreakerOpenError):
        return FirebaseServiceError(
            exc.message,
            status_code=exc.status_code,
            error_code=exc.error_code,
            retryable=True,
            retry_after_seconds=exc.retry_after_seconds,
        )

    if isinstance(
        exc,
        (
            requests.ConnectTimeout,
            requests.ReadTimeout,
        ),
    ):
        timeout_error = ExternalServiceTimeoutError(
            service=FIREBASE_SERVICE_NAME,
            message=(
                "Firebase authentication timed out. "
                "Please try again."
            ),
        )

        return FirebaseServiceError(
            timeout_error.message,
            status_code=timeout_error.status_code,
            error_code=timeout_error.error_code,
            retryable=True,
        )

    if isinstance(exc, requests.ConnectionError):
        unavailable_error = ExternalServiceUnavailableError(
            service=FIREBASE_SERVICE_NAME,
            message=(
                "Firebase authentication is temporarily unreachable. "
                "Please try again."
            ),
        )

        return FirebaseServiceError(
            unavailable_error.message,
            status_code=unavailable_error.status_code,
            error_code=unavailable_error.error_code,
            retryable=True,
        )

    if isinstance(exc, requests.HTTPError):
        response = exc.response
        status_code = (
            response.status_code
            if response is not None
            else 500
        )

        if status_code == 429:
            return FirebaseServiceError(
                "Firebase authentication rate limit exceeded.",
                status_code=429,
                error_code="firebase_rate_limit_exceeded",
                retryable=True,
            )

        if status_code in {
            408,
            409,
            500,
            502,
            503,
            504,
        }:
            return FirebaseServiceError(
                (
                    "Firebase authentication is temporarily unavailable. "
                    "Please try again."
                ),
                status_code=503,
                error_code="firebase_service_unavailable",
                retryable=True,
            )

        if status_code in {400, 401, 403}:
            return FirebaseServiceError(
                "Invalid Firebase token.",
                status_code=401,
                error_code="firebase_invalid_token",
                retryable=False,
            )

        return FirebaseServiceError(
            "Firebase authentication request failed.",
            status_code=status_code,
            error_code="firebase_api_error",
            retryable=False,
        )

    if isinstance(exc, json.JSONDecodeError):
        return FirebaseServiceError(
            "Firebase returned invalid verification JSON.",
            status_code=502,
            error_code="firebase_invalid_json",
            retryable=False,
        )

    if isinstance(exc, requests.RequestException):
        unavailable_error = ExternalServiceUnavailableError(
            service=FIREBASE_SERVICE_NAME,
            message=(
                "Firebase authentication is temporarily unavailable. "
                "Please try again."
            ),
        )

        return FirebaseServiceError(
            unavailable_error.message,
            status_code=unavailable_error.status_code,
            error_code=unavailable_error.error_code,
            retryable=True,
        )

    return FirebaseServiceError(
        "Firebase authentication failed unexpectedly.",
        status_code=500,
        error_code="firebase_unexpected_error",
        retryable=False,
    )


def _execute_firebase_operation(
    operation: Callable[[], T],
    *,
    operation_name: str,
) -> T:
    try:
        return FIREBASE_RESILIENCE.execute(
            operation,
            operation_name=operation_name,
            is_retryable=_is_retryable_firebase_error,
            translate_error=_translate_firebase_error,
            allow_retry=True,
        )
    except CircuitBreakerOpenError as exc:
        translated = _translate_firebase_error(exc)
        raise translated from exc
    except ExternalServiceError:
        raise
    except Exception as exc:
        translated = _translate_firebase_error(exc)
        raise translated from exc


def _firebase_error_to_http_exception(
    exc: ExternalServiceError,
) -> HTTPException:
    detail: dict[str, Any] = {
        "message": exc.message,
        "type": exc.error_code,
        "service": exc.service,
        "retryable": exc.retryable,
    }

    if exc.retry_after_seconds is not None:
        detail["retry_after_seconds"] = exc.retry_after_seconds

    headers = None

    if exc.retry_after_seconds is not None:
        headers = {
            "Retry-After": str(exc.retry_after_seconds),
        }

    return HTTPException(
        status_code=exc.status_code,
        detail=detail,
        headers=headers,
    )


def verify_firebase_token_with_rest(
    token: str,
) -> dict[str, Any]:
    api_key = os.getenv("FIREBASE_API_KEY", "").strip()

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "FIREBASE_API_KEY is missing on backend.",
                "type": "firebase_configuration_error",
            },
        )

    url = (
        "https://identitytoolkit.googleapis.com/v1/"
        f"accounts:lookup?key={api_key}"
    )

    def operation() -> dict[str, Any]:
        response = requests.post(
            url,
            json={"idToken": token},
            timeout=get_firebase_timeout_seconds(),
        )

        if response.status_code != 200:
            response.raise_for_status()

        try:
            payload = response.json()
        except requests.JSONDecodeError as exc:
            raise json.JSONDecodeError(
                exc.msg,
                exc.doc,
                exc.pos,
            ) from exc

        if not isinstance(payload, dict):
            raise FirebaseServiceError(
                "Firebase returned an invalid verification payload.",
                status_code=502,
                error_code="firebase_invalid_payload",
            )

        return payload

    try:
        data = _execute_firebase_operation(
            operation,
            operation_name="verify_id_token",
        )
    except ExternalServiceError as exc:
        raise _firebase_error_to_http_exception(exc) from exc

    users = data.get("users", [])

    if not users:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Firebase user not found.",
                "type": "firebase_user_not_found",
            },
        )

    first_user = users[0]

    if not isinstance(first_user, dict):
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Invalid Firebase user payload.",
                "type": "firebase_invalid_user_payload",
            },
        )

    return first_user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db),
) -> User:
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
    ):
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Missing Authorization Bearer token.",
                "type": "missing_bearer_token",
            },
        )

    token = credentials.credentials.strip()

    if not token:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Empty Firebase token.",
                "type": "empty_firebase_token",
            },
        )

    firebase_user = verify_firebase_token_with_rest(token)

    firebase_uid = _clean_text(
        firebase_user.get("localId")
    )
    email = _clean_text(
        firebase_user.get("email")
    ).lower()
    full_name = _firebase_display_name(
        firebase_user,
        email,
    )

    if not firebase_uid:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Firebase UID missing.",
                "type": "firebase_uid_missing",
            },
        )

    user = (
        db.query(User)
        .filter(User.firebase_uid == firebase_uid)
        .first()
    )

    if not user:
        user = User(
            firebase_uid=firebase_uid,
            email=email,
            full_name=full_name,
            plan="free",
            is_pro=False,
        )

        try:
            db.add(user)
            db.commit()
            db.refresh(user)
        except Exception:
            db.rollback()
            LOGGER.exception(
                "Failed to create authenticated user.",
                extra={
                    "event": "firebase_user_create_failed",
                },
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "User account synchronization failed.",
                    "type": "user_sync_failed",
                },
            )

        return user

    changed = False

    if email and getattr(user, "email", None) != email:
        user.email = email
        changed = True

    current_name = _clean_text(
        getattr(user, "full_name", "")
    )
    normalized_current_name = _clean_display_name(
        current_name
    )

    if full_name and current_name != full_name:
        user.full_name = full_name
        changed = True
    elif (
        normalized_current_name
        and current_name != normalized_current_name
    ):
        user.full_name = normalized_current_name
        changed = True

    if changed:
        try:
            db.add(user)
            db.commit()
            db.refresh(user)
        except Exception:
            db.rollback()
            LOGGER.exception(
                "Failed to update authenticated user profile.",
                extra={
                    "event": "firebase_user_update_failed",
                    "user_id": user.id,
                },
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "User profile synchronization failed.",
                    "type": "user_sync_failed",
                },
            )

    return user


def get_test_user(
    db: Session = Depends(get_db),
) -> User:
    user = (
        db.query(User)
        .filter(
            User.email
            == "local-test@talentmatch.dev"
        )
        .first()
    )

    if user:
        return user

    user = User(
        firebase_uid="local-test-user",
        email="local-test@talentmatch.dev",
        full_name="Local Test User",
        plan="free",
        is_pro=False,
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        LOGGER.exception(
            "Failed to create local test user.",
            extra={
                "event": "local_test_user_create_failed",
            },
        )
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Local test user could not be created.",
                "type": "local_test_user_create_failed",
            },
        )

    return user


def get_firebase_resilience_status() -> dict[str, object]:
    return FIREBASE_RESILIENCE.circuit_breaker.snapshot()
