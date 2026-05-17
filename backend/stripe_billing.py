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

    event_type = event["type"]
    data_object = event["data"]["object"]

    metadata = data_object.get("metadata") or {}
    user_id = metadata.get("user_id")
    email = metadata.get("email") or data_object.get("customer_email")

    if event_type == "checkout.session.completed":
        subscription_id = data_object.get("subscription")

        if subscription_id:
            subscription = stripe.Subscription.retrieve(subscription_id)
            sub_metadata = subscription.get("metadata") or {}
            user_id = user_id or sub_metadata.get("user_id")
            email = email or sub_metadata.get("email")

        user = None

        if user_id:
            user = db.query(User).filter(User.id == int(user_id)).first()

        if user is None and email:
            user = db.query(User).filter(User.email == email).first()

        if user:
            user.plan = "pro"
            user.is_pro = True
            db.add(user)
            db.commit()

            return {
                "status": "ok",
                "event": event_type,
                "upgraded_user_id": user.id,
            }

    if event_type in {"customer.subscription.created", "customer.subscription.updated"}:
        metadata = data_object.get("metadata") or {}
        user_id = metadata.get("user_id")
        email = metadata.get("email")
        status = data_object.get("status", "")

        user = None

        if user_id:
            user = db.query(User).filter(User.id == int(user_id)).first()

        if user is None and email:
            user = db.query(User).filter(User.email == email).first()

        if user:
            if status in {"active", "trialing"}:
                user.plan = "pro"
                user.is_pro = True
            else:
                user.plan = "free"
                user.is_pro = False

            db.add(user)
            db.commit()

            return {
                "status": "ok",
                "event": event_type,
                "user_id": user.id,
                "subscription_status": status,
            }

    if event_type == "customer.subscription.deleted":
        customer_id = data_object.get("customer")
        email = None

        if customer_id:
            customer = stripe.Customer.retrieve(customer_id)
            email = customer.get("email")

        user = db.query(User).filter(User.email == email).first() if email else None

        if user:
            user.plan = "free"
            user.is_pro = False
            db.add(user)
            db.commit()

            return {
                "status": "ok",
                "event": event_type,
                "downgraded_user_id": user.id,
            }

    return {
        "status": "ignored",
        "event": event_type,
    }