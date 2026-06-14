from __future__ import annotations

import os

from .provider import BillingProvider
from .paypal_provider import PayPalBillingProvider


def get_billing_provider() -> BillingProvider:
    provider = os.getenv("BILLING_PROVIDER", "paypal").strip().lower()

    if provider == "paypal":
        return PayPalBillingProvider()

    raise RuntimeError(f"Unsupported BILLING_PROVIDER: {provider}")
