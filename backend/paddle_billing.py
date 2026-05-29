from __future__ import annotations

import hmac
import json
import os
from hashlib import sha256
from typing import Any

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import User


PADDLE_API_KEY = os.getenv("PADDLE_API_KEY", "").strip()
PADDLE_WEBHOOK_SECRET = os.getenv("PADDLE_WEBHOOK_SECRET", "").strip()
PADDLE_PRICE_ID = os.getenv("PADDLE_PRICE_ID", "").strip()
PADDLE_ENVIRONMENT = os.getenv("PADDLE_ENVIRONMENT", "sandbox").strip().lower()

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "https://talentmatch-frontend-dejan.onrender.com",
).rstrip("/")


def get_paddle_api_base_url() -> str:
    if PADDLE_ENVIRONMENT == "production":
        return "https://api.paddle.com"

    return "https://sandbox-api.paddle.com"


def get_paddle_headers() -> dict[str, str]:
    if not PADDLE_API_KEY:
        raise HTTPException(status_code=500, detail="PADDLE_API_KEY is missing.")

    return {
        "Authorization": f"Bearer {PADDLE_API_KEY}",
        "Content-Type": "application/json",
    }


def create_checkout_url(user: User) -> str:
    if not PADDLE_PRICE_ID:
        raise HTTPException(status_code=500, detail="PADDLE_PRICE_ID is missing.")

    user_email = (user.email or "").strip().lower()

    if not user_email:
        raise HTTPException(status_code=400, detail="User email is missing.")

    payload = {
        "items": [
            {
                "price_id": PADDLE_PRICE_ID,
                "quantity": 1,
            }
        ],
        "customer": {
            "email": user_email,
        },
        "custom_data": {
            "user_id": str(user.id),
            "email": user_email,
            "source": "talentmatch_pro",
        },
        "checkout": {
            "url": f"{FRONTEND_URL}/pricing?success=1",
        },
    }

    url = f"{get_paddle_api_base_url()}/transactions"

    try:
        with httpx.Client(timeout=60) as client:
            response = client.post(
                url,
                headers=get_paddle_headers(),
                json=payload,
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Paddle checkout request failed: {exc}",
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Paddle checkout failed: {response.text}",
        )

    data = response.json()
    checkout_url = (
        data.get("data", {})
        .get("checkout", {})
        .get("url")
    )

    if not checkout_url:
        raise HTTPException(
            status_code=502,
            detail=f"Paddle checkout URL missing: {data}",
        )

    return checkout_url


def create_customer_portal_url(user: User) -> str:
    paddle_customer_id = getattr(user, "paddle_customer_id", None)

    if not paddle_customer_id:
        raise HTTPException(
            status_code=400,
            detail="Paddle customer ID is missing. Customer portal is available after first payment.",
        )

    payload = {
        "customer_id": paddle_customer_id,
    }

    url = f"{get_paddle_api_base_url()}/customer-portal-sessions"

    try:
        with httpx.Client(timeout=60) as client:
            response = client.post(
                url,
                headers=get_paddle_headers(),
                json=payload,
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Paddle customer portal request failed: {exc}",
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Paddle customer portal failed: {response.text}",
        )

    data = response.json()
    portal_url = (
        data.get("data", {})
        .get("urls", {})
        .get("general", {})
        .get("overview")
    )

    if not portal_url:
        raise HTTPException(
            status_code=502,
            detail=f"Paddle customer portal URL missing: {data}",
        )

    return portal_url


def verify_paddle_webhook_signature(body: bytes, headers: dict) -> None:
    if not PADDLE_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="PADDLE_WEBHOOK_SECRET is missing.")

    signature_header = (
        headers.get("paddle-signature")
        or headers.get("Paddle-Signature")
        or ""
    )

    if not signature_header:
        raise HTTPException(status_code=400, detail="Missing Paddle signature header.")

    parts = {}

    for item in signature_header.split(";"):
        if "=" in item:
            key, value = item.split("=", 1)
            parts[key.strip()] = value.strip()

    timestamp = parts.get("ts")
    received_signature = parts.get("h1")

    if not timestamp or not received_signature:
        raise HTTPException(status_code=400, detail="Invalid Paddle signature header.")

    signed_payload = f"{timestamp}:{body.decode('utf-8')}".encode("utf-8")

    expected_signature = hmac.new(
        PADDLE_WEBHOOK_SECRET.encode("utf-8"),
        signed_payload,
        sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, received_signature):
        raise HTTPException(status_code=400, detail="Invalid Paddle webhook signature.")


def _get_custom_data(data_object: dict[str, Any]) -> dict[str, Any]:
    custom_data = data_object.get("custom_data") or {}

    if isinstance(custom_data, dict):
        return custom_data

    return {}


def _extract_user_id(data_object: dict[str, Any]) -> int | None:
    custom_data = _get_custom_data(data_object)

    raw_user_id = custom_data.get("user_id")

    if not raw_user_id:
        raw_user_id = data_object.get("user_id")

    if not raw_user_id:
        return None

    try:
        return int(raw_user_id)
    except Exception:
        return None


def _extract_email(data_object: dict[str, Any]) -> str | None:
    custom_data = _get_custom_data(data_object)

    email = custom_data.get("email")

    if email:
        return str(email).strip().lower()

    customer = data_object.get("customer") or {}

    if isinstance(customer, dict):
        email = customer.get("email")

    if email:
        return str(email).strip().lower()

    return None


def _find_user(db: Session, data_object: dict[str, Any]) -> User | None:
    user_id = _extract_user_id(data_object)
    email = _extract_email(data_object)

    user = None

    if user_id is not None:
        user = db.query(User).filter(User.id == user_id).first()

    if user is None and email:
        user = db.query(User).filter(User.email == email).first()

    return user


def _set_user_pro(db: Session, user: User, data_object: dict[str, Any]) -> dict:
    customer_id = data_object.get("customer_id")
    subscription_id = data_object.get("subscription_id") or data_object.get("id")
    status = data_object.get("status", "active")

    if customer_id:
        user.paddle_customer_id = customer_id

    if subscription_id:
        user.paddle_subscription_id = subscription_id

    user.paddle_subscription_status = str(status)
    user.plan = "pro"
    user.is_pro = True

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "status": "ok",
        "message": "User upgraded to Pro.",
        "user_id": user.id,
        "email": user.email,
        "plan": user.plan,
        "is_pro": bool(user.is_pro),
        "paddle_customer_id": user.paddle_customer_id,
        "paddle_subscription_id": user.paddle_subscription_id,
        "paddle_subscription_status": user.paddle_subscription_status,
    }


def _set_user_free(db: Session, user: User, data_object: dict[str, Any]) -> dict:
    status = data_object.get("status", "free")

    user.paddle_subscription_status = str(status)
    user.plan = "free"
    user.is_pro = False

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "status": "ok",
        "message": "User downgraded to Free.",
        "user_id": user.id,
        "email": user.email,
        "plan": user.plan,
        "is_pro": bool(user.is_pro),
        "paddle_subscription_status": user.paddle_subscription_status,
    }


def handle_paddle_webhook(body: bytes, headers: dict, db: Session) -> dict:
    verify_paddle_webhook_signature(body, headers)

    try:
        event = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid Paddle JSON: {exc}")

    event_type = event.get("event_type", "")
    data_object = event.get("data", {}) or {}

    print("=== PADDLE WEBHOOK RECEIVED ===")
    print("EVENT TYPE:", event_type)

    if not isinstance(data_object, dict):
        raise HTTPException(status_code=400, detail="Invalid Paddle webhook data.")

    pro_events = {
        "transaction.completed",
        "subscription.created",
        "subscription.activated",
        "subscription.updated",
    }

    free_events = {
        "subscription.canceled",
        "subscription.past_due",
    }

    if event_type not in pro_events and event_type not in free_events:
        return {
            "status": "ignored",
            "event": event_type,
        }

    user = _find_user(db, data_object)

    if not user:
        return {
            "status": "ignored",
            "reason": "User not found.",
            "event": event_type,
            "custom_data": _get_custom_data(data_object),
        }

    try:
        if event_type in pro_events:
            return _set_user_pro(db, user, data_object)

        if event_type in free_events:
            return _set_user_free(db, user, data_object)

    except Exception as exc:
        db.rollback()
        print("PADDLE WEBHOOK INTERNAL ERROR:", repr(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "status": "ignored",
        "event": event_type,
    }