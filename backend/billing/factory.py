from __future__ import annotations

import os

from .provider import BillingProvider
from .stripe_provider import StripeBillingProvider


def get_billing_provider() -> BillingProvider:
    provider = os.getenv("BILLING_PROVIDER", "stripe").strip().lower()

    if provider == "stripe":
        return StripeBillingProvider()

    raise RuntimeError(f"Unsupported BILLING_PROVIDER: {provider}")