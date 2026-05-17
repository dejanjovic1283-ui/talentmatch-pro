import os

import stripe
from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import User

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "https://talentmatch-frontend-dejan.onrender.com",
).rstrip("/")

STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")


def create_checkout_session(user: User) -> str:
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="STRIPE_SECRET_KEY is missing.")

    if not STRIPE_PRICE_ID:
        raise HTTPException(status_code=500, detail="STRIPE_PRICE_ID is missing.")

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer_email=user.email,
        client_reference_id=str(user.id),
        line_items=[
            {
                "price": STRIPE_PRICE_ID,
                "quantity": 1,
            }
        ],
        metadata={
            "user_id": str(user.id),
            "email": user.email,
        },
        subscription_data={
            "metadata": {
                "user_id": str(user.id),
                "email": user.email,
            }
        },
        success_url=f"{FRONTEND_URL}/pricing?success=1",
        cancel_url=f"{FRONTEND_URL}/pricing?canceled=1",
    )

    if not session.url:
        raise HTTPException(status_code=500, detail="Stripe checkout URL missing.")

    return session.url


def create_customer_portal_url(user: User) -> str:
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="STRIPE_SECRET_KEY is missing.")

    customers = stripe.Customer.list(email=user.email, limit=1)

    if customers.data:
        customer = customers.data[0]
    else:
        customer = stripe.Customer.create(email=user.email)

    portal_session = stripe.billing_portal.Session.create(
        customer=customer.id,
        return_url=f"{FRONTEND_URL}/pricing",
    )

    if not portal_session.url:
        raise HTTPException(status_code=500, detail="Stripe portal URL missing.")

    return portal_session.url


def _get_stripe_value(obj, key, default=None):
    try:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return obj.get(key, default)
    except Exception:
        return getattr(obj, key, default)


def _extract_email(data_object) -> str | None:
    email = _get_stripe_value(data_object, "customer_email")

    if email:
        return email

    metadata = _get_stripe_value(data_object, "metadata", {}) or {}
    email = metadata.get("email")

    if email:
        return email

    customer_details = _get_stripe_value(data_object, "customer_details", {}) or {}

    if isinstance(customer_details, dict):
        email = customer_details.get("email")
    else:
        email = _get_stripe_value(customer_details, "email")

    if email:
        return email

    return None


def _extract_user_id(data_object) -> int | None:
    metadata = _get_stripe_value(data_object, "metadata", {}) or {}

    raw_user_id = metadata.get("user_id") or _get_stripe_value(
        data_object,
        "client_reference_id",
    )

    if not raw_user_id:
        return None

    try:
        return int(raw_user_id)
    except Exception:
        return None


def _find_user(db: Session, user_id: int | None, email: str | None) -> User | None:
    user = None

    if user_id:
        user = db.query(User).filter(User.id == user_id).first()

    if user is None and email:
        user = db.query(User).filter(User.email == email).first()

    return user


def _set_user_pro(db: Session, user: User) -> dict:
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
        "is_pro": user.is_pro,
    }


def _set_user_free(db: Session, user: User) -> dict:
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
        "is_pro": user.is_pro,
    }


def handle_stripe_webhook(body: bytes, signature: str, db: Session) -> dict:
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="STRIPE_WEBHOOK_SECRET is missing.")

    try:
        event = stripe.Webhook.construct_event(
            payload=body,
            sig_header=signature,
            secret=STRIPE_WEBHOOK_SECRET,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid Stripe webhook: {exc}")

    event_type = event.get("type")
    data_object = event.get("data", {}).get("object", {})

    print("STRIPE WEBHOOK EVENT:", event_type)

    try:
        if event_type == "checkout.session.completed":
            user_id = _extract_user_id(data_object)
            email = _extract_email(data_object)

            print("CHECKOUT COMPLETED USER_ID:", user_id)
            print("CHECKOUT COMPLETED EMAIL:", email)

            user = _find_user(db, user_id=user_id, email=email)

            if not user:
                return {
                    "status": "ignored",
                    "reason": "User not found.",
                    "event": event_type,
                    "user_id": user_id,
                    "email": email,
                }

            return _set_user_pro(db, user)

        if event_type in {
            "customer.subscription.created",
            "customer.subscription.updated",
        }:
            metadata = _get_stripe_value(data_object, "metadata", {}) or {}
            raw_user_id = metadata.get("user_id")
            email = metadata.get("email")
            status = _get_stripe_value(data_object, "status", "")

            user_id = None

            if raw_user_id:
                try:
                    user_id = int(raw_user_id)
                except Exception:
                    user_id = None

            user = _find_user(db, user_id=user_id, email=email)

            if not user:
                return {
                    "status": "ignored",
                    "reason": "User not found for subscription event.",
                    "event": event_type,
                    "subscription_status": status,
                    "user_id": user_id,
                    "email": email,
                }

            if status in {"active", "trialing"}:
                return _set_user_pro(db, user)

            return _set_user_free(db, user)

        if event_type == "customer.subscription.deleted":
            metadata = _get_stripe_value(data_object, "metadata", {}) or {}
            raw_user_id = metadata.get("user_id")
            email = metadata.get("email")

            user_id = None

            if raw_user_id:
                try:
                    user_id = int(raw_user_id)
                except Exception:
                    user_id = None

            user = _find_user(db, user_id=user_id, email=email)

            if not user:
                return {
                    "status": "ignored",
                    "reason": "User not found for deleted subscription.",
                    "event": event_type,
                    "user_id": user_id,
                    "email": email,
                }

            return _set_user_free(db, user)

        return {
            "status": "ignored",
            "event": event_type,
        }

    except Exception as exc:
        db.rollback()
        print("STRIPE WEBHOOK INTERNAL ERROR:", repr(exc))

        return {
            "status": "error",
            "event": event_type,
            "error": str(exc),
        }