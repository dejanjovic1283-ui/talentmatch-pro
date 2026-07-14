from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable, TypeVar

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import User
from resilience import (
    CircuitBreakerOpenError,
    ExternalServiceError,
    ExternalServiceTimeoutError,
    ExternalServiceUnavailableError,
    build_resilience_executor,
    get_float_setting,
)

from .provider import BillingProvider


T = TypeVar("T")

LOGGER = logging.getLogger("talentmatch.paypal")

PAYPAL_SERVICE_NAME = "PayPal"
PAYPAL_CONFIGURATION_PREFIX = "PAYPAL"

PAYPAL_ENV = os.getenv("PAYPAL_ENV", "live").strip().lower()
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "").strip()
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "").strip()
PAYPAL_PLAN_ID = os.getenv("PAYPAL_PLAN_ID", "").strip()
PAYPAL_WEBHOOK_ID = os.getenv("PAYPAL_WEBHOOK_ID", "").strip()

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "https://talentmatchcv.com",
).rstrip("/")

PAYPAL_RESILIENCE = build_resilience_executor(
    service=PAYPAL_SERVICE_NAME,
    prefix=PAYPAL_CONFIGURATION_PREFIX,
    logger=LOGGER,
)


class PayPalServiceError(ExternalServiceError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 503,
        error_code: str = "paypal_service_error",
        retryable: bool = False,
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(
            service=PAYPAL_SERVICE_NAME,
            message=message,
            error_code=error_code,
            status_code=status_code,
            retryable=retryable,
            retry_after_seconds=retry_after_seconds,
        )


def get_paypal_api_base_url() -> str:
    if PAYPAL_ENV == "live":
        return "https://api-m.paypal.com"

    return "https://api-m.sandbox.paypal.com"


def get_paypal_timeout_seconds() -> float:
    return get_float_setting(
        "PAYPAL_TIMEOUT_SECONDS",
        30.0,
        minimum=1.0,
        maximum=300.0,
    )


def _safe_setattr(obj: object, attr: str, value: Any) -> None:
    if hasattr(obj, attr):
        setattr(obj, attr, value)


def _safe_paypal_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except Exception:
        return f"PayPal returned HTTP {response.status_code}."

    if not isinstance(payload, dict):
        return f"PayPal returned HTTP {response.status_code}."

    details = payload.get("details")
    if isinstance(details, list) and details:
        first_detail = details[0]
        if isinstance(first_detail, dict):
            description = first_detail.get("description")
            if isinstance(description, str) and description.strip():
                return description.strip()

    message = payload.get("message")
    if isinstance(message, str) and message.strip():
        return message.strip()

    name = payload.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()

    return f"PayPal returned HTTP {response.status_code}."


def _is_retryable_paypal_error(exc: Exception) -> bool:
    if isinstance(
        exc,
        (
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.PoolTimeout,
            httpx.RemoteProtocolError,
        ),
    ):
        return True

    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        return status_code in {408, 409, 429, 502, 503, 504}

    return False


def _translate_paypal_error(exc: Exception) -> ExternalServiceError:
    if isinstance(exc, PayPalServiceError):
        return exc

    if isinstance(exc, CircuitBreakerOpenError):
        return PayPalServiceError(
            exc.message,
            status_code=exc.status_code,
            error_code=exc.error_code,
            retryable=True,
            retry_after_seconds=exc.retry_after_seconds,
        )

    if isinstance(
        exc,
        (
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.PoolTimeout,
        ),
    ):
        timeout_error = ExternalServiceTimeoutError(
            service=PAYPAL_SERVICE_NAME,
            message="PayPal request timed out. Please try again.",
        )
        return PayPalServiceError(
            timeout_error.message,
            status_code=timeout_error.status_code,
            error_code=timeout_error.error_code,
            retryable=True,
        )

    if isinstance(
        exc,
        (
            httpx.ConnectError,
            httpx.RemoteProtocolError,
            httpx.RequestError,
        ),
    ):
        unavailable_error = ExternalServiceUnavailableError(
            service=PAYPAL_SERVICE_NAME,
            message="PayPal is temporarily unreachable. Please try again.",
        )
        return PayPalServiceError(
            unavailable_error.message,
            status_code=unavailable_error.status_code,
            error_code=unavailable_error.error_code,
            retryable=True,
        )

    if isinstance(exc, httpx.HTTPStatusError):
        response = exc.response
        status_code = response.status_code
        message = _safe_paypal_error_message(response)

        if status_code == 429:
            return PayPalServiceError(
                f"PayPal rate limit exceeded: {message}",
                status_code=429,
                error_code="paypal_rate_limit_exceeded",
                retryable=True,
            )

        if status_code in {408, 409, 502, 503, 504}:
            return PayPalServiceError(
                "PayPal is temporarily unavailable. Please try again.",
                status_code=503,
                error_code="paypal_service_unavailable",
                retryable=True,
            )

        return PayPalServiceError(
            f"PayPal request failed: {message}",
            status_code=status_code,
            error_code="paypal_api_error",
            retryable=False,
        )

    if isinstance(exc, json.JSONDecodeError):
        return PayPalServiceError(
            "PayPal returned invalid JSON.",
            status_code=502,
            error_code="paypal_invalid_json",
        )

    return PayPalServiceError(
        "PayPal request failed because of an unexpected service error.",
        status_code=500,
        error_code="paypal_unexpected_error",
    )


def _execute_paypal_operation(
    operation: Callable[[], T],
    *,
    operation_name: str,
    allow_retry: bool,
) -> T:
    try:
        return PAYPAL_RESILIENCE.execute(
            operation,
            operation_name=operation_name,
            is_retryable=_is_retryable_paypal_error,
            translate_error=_translate_paypal_error,
            allow_retry=allow_retry,
        )
    except CircuitBreakerOpenError as exc:
        translated = _translate_paypal_error(exc)
        raise translated from exc
    except ExternalServiceError:
        raise
    except Exception as exc:
        translated = _translate_paypal_error(exc)
        raise translated from exc


def _to_http_exception(exc: ExternalServiceError) -> HTTPException:
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
        headers = {"Retry-After": str(exc.retry_after_seconds)}

    return HTTPException(
        status_code=exc.status_code,
        detail=detail,
        headers=headers,
    )


class PayPalBillingProvider(BillingProvider):
    def _request(
        self,
        *,
        method: str,
        path: str,
        operation_name: str,
        allow_retry: bool,
        auth: tuple[str, str] | None = None,
        headers: dict[str, str] | None = None,
        data: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        url = f"{get_paypal_api_base_url()}{path}"

        def operation() -> httpx.Response:
            with httpx.Client(timeout=get_paypal_timeout_seconds()) as client:
                response = client.request(
                    method=method,
                    url=url,
                    auth=auth,
                    headers=headers,
                    data=data,
                    json=json_body,
                )
                response.raise_for_status()
                return response

        try:
            return _execute_paypal_operation(
                operation,
                operation_name=operation_name,
                allow_retry=allow_retry,
            )
        except ExternalServiceError as exc:
            raise _to_http_exception(exc) from exc

    def _get_access_token(self) -> str:
        if not PAYPAL_CLIENT_ID:
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "PAYPAL_CLIENT_ID is missing.",
                    "type": "paypal_configuration_error",
                },
            )

        if not PAYPAL_CLIENT_SECRET:
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "PAYPAL_CLIENT_SECRET is missing.",
                    "type": "paypal_configuration_error",
                },
            )

        response = self._request(
            method="POST",
            path="/v1/oauth2/token",
            operation_name="oauth_token",
            allow_retry=True,
            auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
            data={"grant_type": "client_credentials"},
            headers={
                "Accept": "application/json",
                "Accept-Language": "en_US",
            },
        )

        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "PayPal returned invalid token JSON.",
                    "type": "paypal_invalid_json",
                },
            ) from exc

        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token.strip():
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "PayPal access token is missing.",
                    "type": "paypal_invalid_token_response",
                },
            )

        return access_token.strip()

    def _paypal_headers(self) -> dict[str, str]:
        token = self._get_access_token()

        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Prefer": "return=representation",
        }

    def create_checkout_url(self, user: User) -> str:
        if not PAYPAL_PLAN_ID:
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "PAYPAL_PLAN_ID is missing.",
                    "type": "paypal_configuration_error",
                },
            )

        user_email = (user.email or "").strip().lower()

        if not user_email:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "User email is missing.",
                    "type": "invalid_user_email",
                },
            )

        payload = {
            "plan_id": PAYPAL_PLAN_ID,
            "custom_id": str(user.id),
            "subscriber": {
                "email_address": user_email,
            },
            "application_context": {
                "brand_name": "TalentMatch Pro",
                "locale": "en-US",
                "shipping_preference": "NO_SHIPPING",
                "user_action": "SUBSCRIBE_NOW",
                "payment_method": {
                    "payer_selected": "PAYPAL",
                    "payee_preferred": "IMMEDIATE_PAYMENT_REQUIRED",
                },
                "return_url": f"{FRONTEND_URL}/pricing?paypal_success=1",
                "cancel_url": f"{FRONTEND_URL}/pricing?paypal_cancel=1",
            },
        }

        LOGGER.info(
            "PayPal subscription creation requested.",
            extra={
                "event": "paypal_subscription_requested",
                "user_id": user.id,
            },
        )

        response = self._request(
            method="POST",
            path="/v1/billing/subscriptions",
            operation_name="create_subscription",
            allow_retry=False,
            headers=self._paypal_headers(),
            json_body=payload,
        )

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "PayPal returned invalid subscription JSON.",
                    "type": "paypal_invalid_json",
                },
            ) from exc

        approve_url = next(
            (
                link.get("href")
                for link in data.get("links", [])
                if isinstance(link, dict)
                and link.get("rel") == "approve"
                and isinstance(link.get("href"), str)
                and link.get("href")
            ),
            None,
        )

        if not approve_url:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "PayPal approval URL is missing.",
                    "type": "paypal_approval_url_missing",
                },
            )

        LOGGER.info(
            "PayPal subscription created.",
            extra={
                "event": "paypal_subscription_created",
                "user_id": user.id,
            },
        )

        return approve_url

    def create_customer_portal_url(self, user: User) -> str:
        return f"{FRONTEND_URL}/customer-portal"

    def _verify_webhook_signature(self, body: bytes, headers: dict) -> None:
        if not PAYPAL_WEBHOOK_ID:
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "PAYPAL_WEBHOOK_ID is missing.",
                    "type": "paypal_configuration_error",
                },
            )

        headers_lower = {
            str(key).lower(): str(value)
            for key, value in headers.items()
        }

        required_headers = {
            "transmission_id": headers_lower.get("paypal-transmission-id"),
            "transmission_time": headers_lower.get("paypal-transmission-time"),
            "cert_url": headers_lower.get("paypal-cert-url"),
            "auth_algo": headers_lower.get("paypal-auth-algo"),
            "transmission_sig": headers_lower.get("paypal-transmission-sig"),
        }

        missing = [
            key
            for key, value in required_headers.items()
            if not value
        ]
        if missing:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": (
                        "Missing PayPal webhook signature headers: "
                        f"{', '.join(missing)}"
                    ),
                    "type": "paypal_webhook_headers_missing",
                },
            )

        try:
            webhook_event = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Invalid PayPal webhook JSON.",
                    "type": "paypal_invalid_webhook_json",
                },
            ) from exc

        if not isinstance(webhook_event, dict):
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Invalid PayPal webhook payload.",
                    "type": "paypal_invalid_webhook_payload",
                },
            )

        verification_payload = {
            **required_headers,
            "webhook_id": PAYPAL_WEBHOOK_ID,
            "webhook_event": webhook_event,
        }

        response = self._request(
            method="POST",
            path="/v1/notifications/verify-webhook-signature",
            operation_name="verify_webhook_signature",
            allow_retry=True,
            headers=self._paypal_headers(),
            json_body=verification_payload,
        )

        try:
            verification_data = response.json()
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "PayPal returned invalid verification JSON.",
                    "type": "paypal_invalid_json",
                },
            ) from exc

        verification_status = verification_data.get("verification_status")

        if verification_status != "SUCCESS":
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Invalid PayPal webhook signature.",
                    "type": "paypal_invalid_webhook_signature",
                },
            )

    def _find_user(
        self,
        db: Session,
        resource: dict[str, Any],
    ) -> User | None:
        custom_id = resource.get("custom_id")

        if custom_id:
            try:
                user_id = int(custom_id)
            except (TypeError, ValueError):
                user_id = None

            if user_id is not None:
                user = (
                    db.query(User)
                    .filter(User.id == user_id)
                    .first()
                )
                if user:
                    return user

        subscription_id = (
            resource.get("id")
            or resource.get("billing_agreement_id")
            or resource.get("subscription_id")
        )

        if subscription_id and hasattr(User, "paypal_subscription_id"):
            user = (
                db.query(User)
                .filter(
                    User.paypal_subscription_id
                    == str(subscription_id)
                )
                .first()
            )
            if user:
                return user

        subscriber = resource.get("subscriber") or {}
        email = (
            subscriber.get("email_address")
            or resource.get("email_address")
        )

        if email:
            normalized_email = str(email).strip().lower()
            return (
                db.query(User)
                .filter(User.email == normalized_email)
                .first()
            )

        return None

    def _set_user_pro(
        self,
        db: Session,
        user: User,
        resource: dict[str, Any],
    ) -> dict:
        subscription_id = (
            resource.get("id")
            or resource.get("billing_agreement_id")
            or resource.get("subscription_id")
        )

        status = resource.get("status") or "ACTIVE"
        subscriber = resource.get("subscriber") or {}

        user.plan = "pro"
        user.is_pro = True

        _safe_setattr(
            user,
            "paypal_subscription_id",
            subscription_id,
        )
        _safe_setattr(
            user,
            "paypal_subscription_status",
            str(status),
        )
        _safe_setattr(
            user,
            "paypal_customer_id",
            subscriber.get("payer_id"),
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        LOGGER.info(
            "User upgraded to Pro through PayPal webhook.",
            extra={
                "event": "paypal_user_upgraded",
                "user_id": user.id,
            },
        )

        return {
            "status": "ok",
            "message": "User upgraded to Pro via PayPal.",
            "user_id": user.id,
            "email": user.email,
            "plan": user.plan,
            "is_pro": bool(user.is_pro),
            "paypal_subscription_id": subscription_id,
            "paypal_subscription_status": str(status),
        }

    def _set_user_free(
        self,
        db: Session,
        user: User,
        resource: dict[str, Any],
    ) -> dict:
        status = resource.get("status") or "inactive"

        user.plan = "free"
        user.is_pro = False

        _safe_setattr(
            user,
            "paypal_subscription_status",
            str(status),
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        LOGGER.info(
            "User downgraded to Free through PayPal webhook.",
            extra={
                "event": "paypal_user_downgraded",
                "user_id": user.id,
            },
        )

        return {
            "status": "ok",
            "message": "User downgraded to Free via PayPal.",
            "user_id": user.id,
            "email": user.email,
            "plan": user.plan,
            "is_pro": bool(user.is_pro),
            "paypal_subscription_status": str(status),
        }

    def handle_webhook(
        self,
        body: bytes,
        headers: dict,
        db: Session,
    ) -> dict:
        self._verify_webhook_signature(
            body=body,
            headers=headers,
        )

        try:
            event = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Invalid PayPal webhook JSON.",
                    "type": "paypal_invalid_webhook_json",
                },
            ) from exc

        if not isinstance(event, dict):
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Invalid PayPal webhook payload.",
                    "type": "paypal_invalid_webhook_payload",
                },
            )

        event_type = str(event.get("event_type", "")).strip()
        resource = event.get("resource", {}) or {}

        LOGGER.info(
            "PayPal webhook received.",
            extra={
                "event": "paypal_webhook_received",
                "paypal_event_type": event_type,
            },
        )

        if not isinstance(resource, dict):
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Invalid PayPal webhook resource.",
                    "type": "paypal_invalid_webhook_resource",
                },
            )

        activate_events = {
            "BILLING.SUBSCRIPTION.CREATED",
            "BILLING.SUBSCRIPTION.ACTIVATED",
            "PAYMENT.SALE.COMPLETED",
        }

        downgrade_events = {
            "BILLING.SUBSCRIPTION.CANCELLED",
            "BILLING.SUBSCRIPTION.EXPIRED",
            "BILLING.SUBSCRIPTION.SUSPENDED",
            "BILLING.SUBSCRIPTION.PAYMENT.FAILED",
        }

        if (
            event_type not in activate_events
            and event_type not in downgrade_events
        ):
            return {
                "status": "ignored",
                "event": event_type,
            }

        user = self._find_user(db, resource)

        if not user:
            LOGGER.warning(
                "PayPal webhook user was not found.",
                extra={
                    "event": "paypal_webhook_user_not_found",
                    "paypal_event_type": event_type,
                },
            )

            return {
                "status": "ignored",
                "reason": "User not found.",
                "event": event_type,
                "custom_id": resource.get("custom_id"),
                "subscription_id": (
                    resource.get("id")
                    or resource.get("billing_agreement_id")
                    or resource.get("subscription_id")
                ),
            }

        try:
            if event_type in activate_events:
                return self._set_user_pro(
                    db,
                    user,
                    resource,
                )

            if event_type in downgrade_events:
                return self._set_user_free(
                    db,
                    user,
                    resource,
                )
        except Exception as exc:
            db.rollback()
            LOGGER.exception(
                "PayPal webhook database update failed.",
                extra={
                    "event": "paypal_webhook_database_error",
                    "paypal_event_type": event_type,
                    "user_id": user.id,
                },
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "PayPal webhook processing failed.",
                    "type": "paypal_webhook_processing_error",
                },
            ) from exc

        return {
            "status": "ignored",
            "event": event_type,
        }


def get_paypal_resilience_status() -> dict[str, object]:
    return PAYPAL_RESILIENCE.circuit_breaker.snapshot()
