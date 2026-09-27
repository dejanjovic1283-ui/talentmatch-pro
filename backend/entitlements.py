"""Server-side entitlement helpers for TalentMatch Pro."""

from __future__ import annotations

import logging
import os
from typing import Final

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models import User


LOGGER = logging.getLogger("talentmatch.entitlements")

PRO_ACCESS_OVERRIDE_EMAILS_ENV: Final[str] = "PRO_ACCESS_OVERRIDE_EMAILS"


def _normalise_email(value: object) -> str:
    return str(value or "").strip().lower()


def configured_pro_override_emails() -> frozenset[str]:
    """Return the private, operator-configured Pro override identities."""

    raw_value = os.getenv(PRO_ACCESS_OVERRIDE_EMAILS_ENV, "")
    return frozenset(
        email
        for email in (_normalise_email(item) for item in raw_value.split(","))
        if email
    )


def is_pro_access_override(user_or_email: User | str | None) -> bool:
    """Return whether one identity has an explicit server-side Pro override."""

    if isinstance(user_or_email, str):
        email = _normalise_email(user_or_email)
    else:
        email = _normalise_email(getattr(user_or_email, "email", ""))

    return bool(email) and email in configured_pro_override_emails()


def has_pro_access(user: User | None) -> bool:
    """Return the effective backend entitlement for a persisted user."""

    if user is None:
        return False

    return bool(getattr(user, "is_pro", False)) or is_pro_access_override(user)


def apply_pro_access_override(db: Session, user: User) -> User:
    """Persist the configured owner override without changing other users."""

    if not is_pro_access_override(user):
        return user

    changed = (
        not bool(getattr(user, "is_pro", False))
        or str(getattr(user, "plan", "")).strip().lower() != "pro"
    )

    if not changed:
        return user

    user.plan = "pro"
    user.is_pro = True

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except SQLAlchemyError:
        db.rollback()
        # Keep the current authenticated request Pro even when a transient
        # persistence failure prevents the repair from being committed. The
        # next authenticated request will retry the same idempotent repair.
        user.plan = "pro"
        user.is_pro = True
        LOGGER.exception(
            "Configured Pro entitlement override could not be persisted.",
            extra={
                "event": "pro_access_override_persist_failed",
                "user_id": getattr(user, "id", None),
                "retryable": True,
            },
        )
    else:
        LOGGER.info(
            "Configured Pro entitlement override applied.",
            extra={
                "event": "pro_access_override_applied",
                "user_id": getattr(user, "id", None),
            },
        )

    return user
