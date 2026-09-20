import logging
import os
from typing import Final

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from models import AnalysisRecord, User

LOGGER = logging.getLogger(__name__)

DEFAULT_FREE_PLAN_ANALYSIS_LIMIT: Final[int] = 3
CV_ANALYSIS_TYPE: Final[str] = "cv_analysis"

KNOWN_ANALYSIS_TYPES: Final[tuple[str, ...]] = (
    "cv_analysis",
    "ats_checker",
    "cv_rewrite",
    "semantic_match",
    "recruiter_mode",
)


def _read_nonnegative_int_env(name: str, default: int) -> int:
    """Read a non-negative integer environment variable safely."""
    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        LOGGER.warning(
            "Invalid integer environment value; using default.",
            extra={
                "event": "invalid_integer_environment_value",
                "environment_variable": name,
            },
        )
        return default

    if value < 0:
        LOGGER.warning(
            "Negative integer environment value; using default.",
            extra={
                "event": "negative_integer_environment_value",
                "environment_variable": name,
            },
        )
        return default

    return value


FREE_PLAN_ANALYSIS_LIMIT: Final[int] = _read_nonnegative_int_env(
    "FREE_PLAN_ANALYSIS_LIMIT",
    DEFAULT_FREE_PLAN_ANALYSIS_LIMIT,
)


def _analysis_counts_by_type(db: Session, user_id: int) -> dict[str, int]:
    """Return lifetime persisted analysis counts grouped by analysis type."""
    rows = (
        db.query(
            AnalysisRecord.analysis_type,
            func.count(AnalysisRecord.id),
        )
        .filter(AnalysisRecord.user_id == user_id)
        .group_by(AnalysisRecord.analysis_type)
        .all()
    )

    counts: dict[str, int] = {}

    for analysis_type, count in rows:
        normalized_type = str(analysis_type or CV_ANALYSIS_TYPE).strip().lower()
        if not normalized_type:
            normalized_type = CV_ANALYSIS_TYPE

        counts[normalized_type] = counts.get(normalized_type, 0) + int(count or 0)

    return counts


def _build_usage_by_type(raw_counts: dict[str, int]) -> dict[str, int]:
    """Build a stable usage payload while preserving unexpected future types."""
    usage_by_type = {
        analysis_type: int(raw_counts.get(analysis_type, 0))
        for analysis_type in KNOWN_ANALYSIS_TYPES
    }

    for analysis_type, count in raw_counts.items():
        if analysis_type not in usage_by_type:
            usage_by_type[analysis_type] = int(count)

    return usage_by_type


def _sync_legacy_cv_analysis_counter(
    db: Session,
    user: User,
    cv_analyses_used: int,
) -> None:
    """
    Keep users.analyses_used compatible with the Free-plan CV Analysis counter.

    The authoritative usage source is AnalysisRecord. This legacy User column is
    synchronized only when its value differs, avoiding an unnecessary write on
    every profile/usage read.
    """
    if int(getattr(user, "analyses_used", 0) or 0) == cv_analyses_used:
        return

    try:
        user.analyses_used = cv_analyses_used
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        LOGGER.exception(
            "Failed to synchronize legacy CV analysis usage counter.",
            extra={
                "event": "legacy_usage_counter_sync_failed",
                "user_id": getattr(user, "id", None),
            },
        )


def get_user_usage(db: Session, user: User) -> dict:
    """
    Return authoritative lifetime usage for one TalentMatch Pro user.

    Free-plan enforcement applies only to persisted ``cv_analysis`` records.
    ATS Checker and the other analysis types remain visible in the usage
    breakdown but do not consume the Free plan's CV Analysis allowance.
    """
    raw_counts = _analysis_counts_by_type(db, user.id)
    usage_by_type = _build_usage_by_type(raw_counts)

    cv_analyses_used = int(usage_by_type.get(CV_ANALYSIS_TYPE, 0))
    total_analyses = sum(usage_by_type.values())

    _sync_legacy_cv_analysis_counter(
        db,
        user,
        cv_analyses_used,
    )

    is_pro = bool(user.is_pro)
    remaining = max(0, FREE_PLAN_ANALYSIS_LIMIT - cv_analyses_used)

    return {
        "plan": user.plan,
        "is_pro": is_pro,
        "analyses_used": cv_analyses_used,
        "cv_analyses_used": cv_analyses_used,
        "total_analyses": total_analyses,
        "usage_by_type": usage_by_type,
        "usage_period": "lifetime",
        "free_limit": FREE_PLAN_ANALYSIS_LIMIT,
        "remaining": None if is_pro else remaining,
        "upgrade_required": (
            not is_pro
            and cv_analyses_used >= FREE_PLAN_ANALYSIS_LIMIT
        ),
    }


def ensure_analysis_allowed(db: Session, user: User) -> None:
    """Enforce the Free plan limit for CV Analysis only."""
    if bool(user.is_pro):
        return

    usage = get_user_usage(db, user)

    if usage["cv_analyses_used"] >= FREE_PLAN_ANALYSIS_LIMIT:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Free plan CV Analysis limit reached. Please upgrade to Pro.",
                **usage,
            },
        )
