from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import User

from .provider import BillingProvider


PAYPAL_ENV = os.getenv("PAYPAL_ENV", "live").strip().lower()
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "").strip()
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "").strip()
PAYPAL_PLAN_ID = os.getenv("PAYPAL_PLAN_ID", "").strip()
PAYPAL_WEBHOOK_ID = os.getenv("PAYPAL_WEBHOOK_ID", "").strip()

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "https://talentmatch-frontend-dejan.onrender.com",
).rstrip("/")


def get_paypal_api_base_url() -> str:
    if PAYPAL_ENV == "live":
        return "https://api-m.paypal.com"

    return "https://api-m.sandbox.paypal.com"


def _safe_setattr(obj: object, attr: str, value: Any) -> None:
    if hasattr(obj, attr):
        setattr(obj, attr, value)


class PayPalBillingProvider(BillingProvider):
    def _raise_paypal_error(self, response: httpx.Response, context: str) -> None:
        print(f"=== PAYPAL ERROR: {context} ===")
        print("STATUS:", response.status_code)
        print("BODY:", response.text)

        raise HTTPException(
            status_code=response.status_code,
            detail={
                "message": context,
                "paypal_status_code": response.status_code,
                "paypal_response": response.text,
            },
        )

    def _get_access_token(self) -> str:
        if not PAYPAL_CLIENT_ID:
            raise HTTPException(status_code=500, detail="PAYPAL_CLIENT_ID is missing.")

        if not PAYPAL_CLIENT_SECRET:
            raise HTTPException(status_code=500, detail="PAYPAL_CLIENT_SECRET is missing.")

        try:
            with httpx.Client(timeout=60) as client:
                response = client.post(
                    f"{get_paypal_api_base_url()}/v1/oauth2/token",
                    auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
                    data={"grant_type": "client_credentials"},
                    headers={
                        "Accept": "application/json",
                        "Accept-Language": "en_US",
                    },
                )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"PayPal token request failed: {exc}",
            ) from exc

        if response.status_code >= 400:
            self._raise_paypal_error(response, "PayPal token request failed.")

        return response.json()["access_token"]

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
            raise HTTPException(status_code=500, detail="PAYPAL_PLAN_ID is missing.")

        user_email = (user.email or "").strip().lower()

        if not user_email:
            raise HTTPException(status_code=400, detail="User email is missing.")

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

        print("=== CREATING PAYPAL SUBSCRIPTION ===")
        print("PAYPAL_ENV:", PAYPAL_ENV)
        print("PAYPAL_PLAN_ID:", PAYPAL_PLAN_ID)
        print("USER:", user.id, user_email)

        try:
            with httpx.Client(timeout=60) as client:
                response = client.post(
                    f"{get_paypal_api_base_url()}/v1/billing/subscriptions",
                    headers=self._paypal_headers(),
                    json=payload,
                )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"PayPal subscription request failed: {exc}",
            ) from exc

        if response.status_code >= 400:
            self._raise_paypal_error(response, "PayPal subscription creation failed.")

        data = response.json()

        approve_url = None
        for link in data.get("links", []):
            if link.get("rel") == "approve":
                approve_url = link.get("href")
                break

        if not approve_url:
            raise HTTPException(
                status_code=502,
                detail=f"PayPal approval URL missing: {data}",
            )

        print("PAYPAL SUBSCRIPTION CREATED:", data.get("id"))

        return approve_url

    def create_customer_portal_url(self, user: User) -> str:
        return "https://www.paypal.com/myaccount/autopay/"

    def _verify_webhook_signature(self, body: bytes, headers: dict) -> None:
        if not PAYPAL_WEBHOOK_ID:
            raise HTTPException(status_code=500, detail="PAYPAL_WEBHOOK_ID is missing.")

        headers_lower = {str(k).lower(): str(v) for k, v in headers.items()}

        required_headers = {
            "transmission_id": headers_lower.get("paypal-transmission-id"),
            "transmission_time": headers_lower.get("paypal-transmission-time"),
            "cert_url": headers_lower.get("paypal-cert-url"),
            "auth_algo": headers_lower.get("paypal-auth-algo"),
            "transmission_sig": headers_lower.get("paypal-transmission-sig"),
        }

        missing = [key for key, value in required_headers.items() if not value]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing PayPal webhook signature headers: {', '.join(missing)}",
            )

        try:
            webhook_event = httpx.Response(200, content=body).json()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid PayPal webhook JSON: {exc}") from exc

        verification_payload = {
            **required_headers,
            "webhook_id": PAYPAL_WEBHOOK_ID,
            "webhook_event": webhook_event,
        }

        try:
            with httpx.Client(timeout=60) as client:
                response = client.post(
                    f"{get_paypal_api_base_url()}/v1/notifications/verify-webhook-signature",
                    headers=self._paypal_headers(),
                    json=verification_payload,
                )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"PayPal webhook verification failed: {exc}",
            ) from exc

        if response.status_code >= 400:
            self._raise_paypal_error(response, "PayPal webhook verification failed.")

        verification_status = response.json().get("verification_status")

        if verification_status != "SUCCESS":
            raise HTTPException(
                status_code=400,
                detail=f"Invalid PayPal webhook signature: {verification_status}",
            )

    def _find_user(self, db: Session, resource: dict[str, Any]) -> User | None:
        custom_id = resource.get("custom_id")

        if custom_id:
            try:
                user_id = int(custom_id)
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    return user
            except Exception:
                pass

        subscription_id = (
            resource.get("id")
            or resource.get("billing_agreement_id")
            or resource.get("subscription_id")
        )

        if subscription_id and hasattr(User, "paypal_subscription_id"):
            user = (
                db.query(User)
                .filter(User.paypal_subscription_id == str(subscription_id))
                .first()
            )
            if user:
                return user

        subscriber = resource.get("subscriber") or {}
        email = subscriber.get("email_address") or resource.get("email_address")

        if email:
            return db.query(User).filter(User.email == str(email).strip().lower()).first()

        return None

    def _set_user_pro(self, db: Session, user: User, resource: dict[str, Any]) -> dict:
        subscription_id = (
            resource.get("id")
            or resource.get("billing_agreement_id")
            or resource.get("subscription_id")
        )

        status = resource.get("status") or "ACTIVE"
        subscriber = resource.get("subscriber") or {}

        user.plan = "pro"
        user.is_pro = True

        _safe_setattr(user, "paypal_subscription_id", subscription_id)
        _safe_setattr(user, "paypal_subscription_status", str(status))
        _safe_setattr(user, "paypal_customer_id", subscriber.get("payer_id"))

        db.add(user)
        db.commit()
        db.refresh(user)

        print("PAYPAL USER UPGRADED TO PRO")
        print("USER ID:", user.id)
        print("EMAIL:", user.email)
        print("PLAN:", user.plan)
        print("IS_PRO:", bool(user.is_pro))
        print("PAYPAL SUBSCRIPTION ID:", subscription_id)
        print("PAYPAL SUBSCRIPTION STATUS:", str(status))

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

    def _set_user_free(self, db: Session, user: User, resource: dict[str, Any]) -> dict:
        status = resource.get("status") or "inactive"

        user.plan = "free"
        user.is_pro = False

        _safe_setattr(user, "paypal_subscription_status", str(status))

        db.add(user)
        db.commit()
        db.refresh(user)

        print("PAYPAL USER DOWNGRADED TO FREE")
        print("USER ID:", user.id)
        print("EMAIL:", user.email)
        print("PLAN:", user.plan)
        print("IS_PRO:", bool(user.is_pro))
        print("PAYPAL SUBSCRIPTION STATUS:", str(status))

        return {
            "status": "ok",
            "message": "User downgraded to Free via PayPal.",
            "user_id": user.id,
            "email": user.email,
            "plan": user.plan,
            "is_pro": bool(user.is_pro),
            "paypal_subscription_status": str(status),
        }

    def handle_webhook(self, body: bytes, headers: dict, db: Session) -> dict:
        self._verify_webhook_signature(body=body, headers=headers)

        try:
            event = httpx.Response(200, content=body).json()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid PayPal webhook JSON: {exc}") from exc

        event_type = event.get("event_type", "")
        resource = event.get("resource", {}) or {}

        print("=== PAYPAL WEBHOOK RECEIVED ===")
        print("EVENT TYPE:", event_type)
        print("FULL PAYPAL EVENT:", event)
        print("RESOURCE:", resource)

        if not isinstance(resource, dict):
            raise HTTPException(status_code=400, detail="Invalid PayPal webhook resource.")

        print("CUSTOM ID:", resource.get("custom_id"))
        print("SUBSCRIPTION ID:", resource.get("id"))
        print("BILLING AGREEMENT ID:", resource.get("billing_agreement_id"))
        print("RESOURCE EMAIL:", resource.get("email_address"))

        subscriber = resource.get("subscriber", {}) or {}
        print("SUBSCRIBER:", subscriber)
        print("SUBSCRIBER EMAIL:", subscriber.get("email_address"))

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

        if event_type not in activate_events and event_type not in downgrade_events:
            return {
                "status": "ignored",
                "event": event_type,
            }

        user = self._find_user(db, resource)

        if not user:
            print("PAYPAL WEBHOOK USER NOT FOUND")
            print("EVENT TYPE:", event_type)
            print("CUSTOM ID:", resource.get("custom_id"))
            print(
                "SUBSCRIPTION ID:",
                resource.get("id")
                or resource.get("billing_agreement_id")
                or resource.get("subscription_id"),
            )
            print("EMAIL:", subscriber.get("email_address") or resource.get("email_address"))

            return {
                "status": "ignored",
                "reason": "User not found.",
                "event": event_type,
                "custom_id": resource.get("custom_id"),
                "subscription_id": resource.get("id")
                or resource.get("billing_agreement_id")
                or resource.get("subscription_id"),
                "email": subscriber.get("email_address") or resource.get("email_address"),
            }

        try:
            if event_type in activate_events:
                return self._set_user_pro(db, user, resource)

            if event_type in downgrade_events:
                return self._set_user_free(db, user, resource)

        except Exception as exc:
            db.rollback()
            print("PAYPAL WEBHOOK INTERNAL ERROR:", repr(exc))
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return {
            "status": "ignored",
            "event": event_type,
        }