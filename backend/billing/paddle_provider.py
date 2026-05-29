from __future__ import annotations

from sqlalchemy.orm import Session

from models import User
from paddle_billing import (
    create_checkout_url,
    create_customer_portal_url,
    handle_paddle_webhook,
)

from .provider import BillingProvider


class PaddleBillingProvider(BillingProvider):
    def create_checkout_url(self, user: User) -> str:
        return create_checkout_url(user)

    def create_customer_portal_url(self, user: User) -> str:
        return create_customer_portal_url(user)

    def handle_webhook(self, body: bytes, headers: dict, db: Session) -> dict:
        return handle_paddle_webhook(body, headers, db)