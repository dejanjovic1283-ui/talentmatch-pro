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

    user_email = (user.email or "").strip().lower()

    if not user_email:
        raise HTTPException(status_code=400, detail="User email is missing.")

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer_email=user_email,
        client_reference_id=str(user.id),
        line_items=[
            {
                "price": STRIPE_PRICE_ID,
                "quantity": 1,
            }
        ],
        metadata={
            "user_id": str(user.id),
            "email": user_email,
        },
        subscription_data={
            "metadata": {
                "user_id": str(user.id),
                "email": user_email,
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

    user_email = (user.email or "").strip().lower()

    if not user_email:
        raise HTTPException(status_code=400, detail="User email is missing.")

    try:
        customers = stripe.Customer.search(query=f"email:'{user_email}'", limit=1)
    except Exception:
        customers = stripe.Customer.list(email=user_email, limit=1)

    if customers.data:
        customer = customers.data[0]
    else:
        customer = stripe.Customer.create(email=user_email)

    portal_session = stripe.billing_portal.Session.create(
        customer=customer.id,
        return_url=f"{FRONTEND_URL}/pricing",
    )

    if not portal_session.url:
        raise HTTPException(status_code=500, detail="Stripe portal URL missing.")

    return portal_session.url


def _get_value(obj, key, default=None):
    if obj is None:
        return default

    try:
        if isinstance(obj, dict):
            return obj.get(key, default)

        return obj.get(key, default)
    except Exception:
        return getattr(obj, key, default)


def _normalize_email(email) -> str | None:
    if not email:
        return None

    email = str(email).strip().lower()

    if not email:
        return None

    return email


def _extract_email(data_object) -> str | None:
    email = _normalize_email(_get_value(data_object, "customer_email"))

    if email:
        return email

    metadata = _get_value(data_object, "metadata", {}) or {}

    if isinstance(metadata, dict):
        email = _normalize_email(metadata.get("email"))

        if email:
            return email

    customer_details = _get_value(data_object, "customer_details", {}) or {}

    if isinstance(customer_details, dict):
        email = _normalize_email(customer_details.get("email"))
    else:
        email = _normalize_email(_get_value(customer_details, "email"))

    if email:
        return email

    customer_id = _get_value(data_object, "customer")

    if customer_id:
        try:
            customer = stripe.Customer.retrieve(customer_id)
            email = _normalize_email(_get_value(customer, "email"))

            if email:
                return email
        except Exception as exc:
            print("COULD NOT RETRIEVE STRIPE CUSTOMER EMAIL:", repr(exc))

    return None


def _extract_user_id(data_object) -> int | None:
    metadata = _get_value(data_object, "metadata", {}) or {}

    raw_user_id = None

    if isinstance(metadata, dict):
        raw_user_id = metadata.get("user_id")

    if not raw_user_id:
        raw_user_id = _get_value(data_object, "client_reference_id")

    if not raw_user_id:
        return None

    try:
        return int(raw_user_id)
    except Exception:
        return None


def _get_subscription_metadata(subscription_id: str | None) -> dict:
    if not subscription_id:
        return {}

    try:
        subscription = stripe.Subscription.retrieve(subscription_id)
        metadata = _get_value(subscription, "metadata", {}) or {}

        if isinstance(metadata, dict):
            return dict(metadata)

        return {}
    except Exception as exc:
        print("COULD NOT RETRIEVE SUBSCRIPTION METADATA:", repr(exc))
        return {}


def _find_user(db: Session, user_id: int | None, email: str | None) -> User | None:
    user = None

    if user_id is not None:
        user = db.query(User).filter(User.id == user_id).first()

    if user is None and email:
        clean_email = email.strip().lower()

        user = db.query(User).filter(User.email == clean_email).first()

        if user is None:
            users = db.query(User).all()

            for candidate in users:
                candidate_email = (candidate.email or "").strip().lower()

                if candidate_email == clean_email:
                    user = candidate
                    break

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
        "is_pro": bool(user.is_pro),
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
        "is_pro": bool(user.is_pro),
    }


def _extract_subscription_identity(data_object) -> tuple[int | None, str | None]:
    metadata = _get_value(data_object, "metadata", {}) or {}

    raw_user_id = None
    email = None

    if isinstance(metadata, dict):
        raw_user_id = metadata.get("user_id")
        email = _normalize_email(metadata.get("email"))

    user_id = None

    if raw_user_id:
        try:
            user_id = int(raw_user_id)
        except Exception:
            user_id = None

    if email is None:
        customer_id = _get_value(data_object, "customer")

        if customer_id:
            try:
                customer = stripe.Customer.retrieve(customer_id)
                email = _normalize_email(_get_value(customer, "email"))
            except Exception as exc:
                print("COULD NOT RETRIEVE CUSTOMER FOR SUBSCRIPTION:", repr(exc))

    return user_id, email


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

    print("=== STRIPE WEBHOOK EVENT ===")
    print("EVENT TYPE:", event_type)

    try:
        if event_type == "checkout.session.completed":
            user_id = _extract_user_id(data_object)
            email = _extract_email(data_object)

            if user_id is None or email is None:
                subscription_id = _get_value(data_object, "subscription")
                subscription_metadata = _get_subscription_metadata(subscription_id)

                if user_id is None and subscription_metadata.get("user_id"):
                    try:
                        user_id = int(subscription_metadata.get("user_id"))
                    except Exception:
                        user_id = None

                if email is None and subscription_metadata.get("email"):
                    email = _normalize_email(subscription_metadata.get("email"))

            print("CHECKOUT USER_ID:", user_id)
            print("CHECKOUT EMAIL:", email)

            user = _find_user(db, user_id=user_id, email=email)

            print("CHECKOUT USER FOUND:", bool(user))

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
            status = _get_value(data_object, "status", "")
            user_id, email = _extract_subscription_identity(data_object)

            print("SUBSCRIPTION EVENT:", event_type)
            print("SUBSCRIPTION STATUS:", status)
            print("SUBSCRIPTION USER_ID:", user_id)
            print("SUBSCRIPTION EMAIL:", email)

            user = _find_user(db, user_id=user_id, email=email)

            print("SUBSCRIPTION USER FOUND:", bool(user))

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
            user_id, email = _extract_subscription_identity(data_object)

            print("SUBSCRIPTION DELETED USER_ID:", user_id)
            print("SUBSCRIPTION DELETED EMAIL:", email)

            user = _find_user(db, user_id=user_id, email=email)

            print("SUBSCRIPTION DELETED USER FOUND:", bool(user))

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