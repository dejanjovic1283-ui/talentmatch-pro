from __future__ import annotations

from abc import ABC, abstractmethod
from sqlalchemy.orm import Session

from models import User


class BillingProvider(ABC):
    @abstractmethod
    def create_checkout_url(self, user: User) -> str:
        raise NotImplementedError

    @abstractmethod
    def create_customer_portal_url(self, user: User) -> str:
        raise NotImplementedError

    @abstractmethod
    def handle_webhook(self, body: bytes, headers: dict, db: Session) -> dict:
        raise NotImplementedError