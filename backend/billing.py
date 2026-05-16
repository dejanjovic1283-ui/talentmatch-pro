import hmac
import os
from hashlib import sha256


def create_checkout_url(email: str, user_id: int) -> str:
    """
    Returns a checkout URL.

    Demo mode:
    returns a fake internal URL that frontend uses
    to trigger instant Pro upgrade.

    Real Lemon mode:
    returns actual Lemon checkout URL.
    """

    demo_mode = os.getenv(
        "DEMO_BILLING_MODE",
        "true",
    ).lower() == "true"

    if demo_mode:
        return "demo://upgrade-to-pro"

    checkout_url = os.getenv(
        "LEMON_SQUEEZY_CHECKOUT_URL",
        "",
    ).strip()

    if not checkout_url:
        raise RuntimeError(
            "LEMON_SQUEEZY_CHECKOUT_URL is missing."
        )

    return checkout_url


def verify_webhook_signature(
    body: bytes,
    signature: str,
) -> bool:
    """
    Verify Lemon webhook signature.

    In demo mode:
    always returns True.
    """

    secret = os.getenv(
        "LEMON_SQUEEZY_WEBHOOK_SECRET",
        "",
    ).strip()

    if not secret:
        return True

    expected = hmac.new(
        secret.encode("utf-8"),
        body,
        sha256,
    ).hexdigest()

    return hmac.compare_digest(
        expected,
        signature,
    )