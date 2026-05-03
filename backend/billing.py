import hashlib
import hmac
import os
from urllib.parse import urlencode


def create_checkout_url(email: str, user_id: int) -> str:
    """Build a Lemon Squeezy checkout URL with prefills and custom user data."""
    checkout_url = os.getenv("LEMON_SQUEEZY_CHECKOUT_URL", "").strip()
    if not checkout_url:
        raise RuntimeError("LEMON_SQUEEZY_CHECKOUT_URL is missing.")

    pairs = [
        ("checkout[email]", email),
        ("checkout[custom][user_id]", str(user_id)),
    ]
    separator = "&" if "?" in checkout_url else "?"
    return f"{checkout_url}{separator}{urlencode(pairs)}"


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """Validate the Lemon Squeezy webhook signature with HMAC-SHA256."""
    webhook_secret = os.getenv("LEMON_SQUEEZY_WEBHOOK_SECRET", "").strip()
    if not webhook_secret or not signature:
        return False

    expected_signature = hmac.new(
        webhook_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)
