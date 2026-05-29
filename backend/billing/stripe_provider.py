from __future__ import annotations

from sqlalchemy.orm import Session

from models import User
from stripe_billing import (
    create_checkout_session,
    create_customer_portal_url,
    handle_stripe_webhook,
)

from .provider import BillingProvider


class StripeBillingProvider(BillingProvider):
    def create_checkout_url(self, user: User) -> str:
        return create_checkout_session(user)

    def create_customer_portal_url(self, user: User) -> str:
        return create_customer_portal_url(user)

    def handle_webhook(self, body: bytes, headers: dict, db: Session) -> dict:
        signature = headers.get("stripe-signature", "")
        return handle_stripe_webhook(body, signature, db)