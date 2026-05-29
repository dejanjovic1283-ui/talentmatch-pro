from __future__ import annotations

import os

from .provider import BillingProvider
from .paddle_provider import PaddleBillingProvider


def get_billing_provider() -> BillingProvider:
    provider = os.getenv("BILLING_PROVIDER", "paddle").strip().lower()

    if provider == "paddle":
        return PaddleBillingProvider()

    raise RuntimeError(f"Unsupported BILLING_PROVIDER: {provider}")