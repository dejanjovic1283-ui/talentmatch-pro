import os

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import AnalysisRecord, User

FREE_PLAN_ANALYSIS_LIMIT = int(os.getenv("FREE_PLAN_ANALYSIS_LIMIT", "3"))


def get_user_usage(db: Session, user: User) -> dict:
    used = (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.user_id == user.id)
        .count()
    )

    try:
        user.analyses_used = used
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()

    remaining = max(0, FREE_PLAN_ANALYSIS_LIMIT - used)

    return {
        "plan": user.plan,
        "is_pro": user.is_pro,
        "analyses_used": used,
        "free_limit": FREE_PLAN_ANALYSIS_LIMIT,
        "remaining": remaining,
        "upgrade_required": not user.is_pro and used >= FREE_PLAN_ANALYSIS_LIMIT,
    }


def ensure_analysis_allowed(db: Session, user: User) -> None:
    usage = get_user_usage(db, user)

    if user.is_pro:
        return

    if usage["analyses_used"] >= FREE_PLAN_ANALYSIS_LIMIT:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Free plan limit reached. Please upgrade to Pro.",
                **usage,
            },
        )