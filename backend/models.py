from __future__ import annotations

from datetime import datetime, timezone
from typing import Final

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, false, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


DEFAULT_PLAN: Final[str] = "free"
DEFAULT_ANALYSIS_TYPE: Final[str] = "cv_analysis"
DEFAULT_CANDIDATE_STATUS: Final[str] = "new"
DEFAULT_CANDIDATE_SOURCE: Final[str] = "recruiter_mode"
DEFAULT_RECRUITER_JOB_STATUS: Final[str] = "queued"
EMPTY_JSON_LIST: Final[str] = "[]"


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for ORM-side defaults."""
    return datetime.now(timezone.utc)


class User(Base):
    """Application user synchronized with Firebase Authentication."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    firebase_uid: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    plan: Mapped[str] = mapped_column(
        String(50),
        default=DEFAULT_PLAN,
        server_default=text("'free'"),
        nullable=False,
    )
    is_pro: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
        nullable=False,
    )
    analyses_used: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
    )

    paypal_customer_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    paypal_subscription_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    paypal_subscription_status: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    analyses: Mapped[list["AnalysisRecord"]] = relationship(
        "AnalysisRecord",
        back_populates="user",
    )
    recruiter_candidates: Mapped[list["RecruiterCandidate"]] = relationship(
        "RecruiterCandidate",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    recruiter_jobs: Mapped[list["RecruiterJob"]] = relationship(
        "RecruiterJob",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"User(id={self.id!r}, plan={self.plan!r}, "
            f"is_pro={self.is_pro!r})"
        )


class AnalysisRecord(Base):
    """Persist a CV analysis result for history and usage accounting."""

    __tablename__ = "analysis_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
        nullable=False,
    )

    cv_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cv_storage_path: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )

    job_description: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(
        Text,
        default="",
        server_default=text("''"),
        nullable=False,
    )
    matched_skills: Mapped[str] = mapped_column(
        Text,
        default=EMPTY_JSON_LIST,
        server_default=text("'[]'"),
        nullable=False,
    )
    missing_skills: Mapped[str] = mapped_column(
        Text,
        default=EMPTY_JSON_LIST,
        server_default=text("'[]'"),
        nullable=False,
    )
    recommendations: Mapped[str] = mapped_column(
        Text,
        default=EMPTY_JSON_LIST,
        server_default=text("'[]'"),
        nullable=False,
    )
    analysis_type: Mapped[str] = mapped_column(
        String(50),
        default=DEFAULT_ANALYSIS_TYPE,
        server_default=text("'cv_analysis'"),
        index=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="analyses",
    )

    def __repr__(self) -> str:
        return (
            f"AnalysisRecord(id={self.id!r}, user_id={self.user_id!r}, "
            f"analysis_type={self.analysis_type!r}, score={self.score!r})"
        )


class RecruiterCandidate(Base):
    """
    Persist candidates produced by Recruiter Mode.

    This model supports the TalentMatch Pro Recruiter Workspace, including
    the candidate database, favorites, tags, recruiter notes, job projects,
    filtering and dashboard views.
    """

    __tablename__ = "recruiter_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
        nullable=False,
    )

    filename: Mapped[str] = mapped_column(
        String(255), index=True, nullable=False
    )
    cv_storage_path: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )

    job_description: Mapped[str] = mapped_column(Text, nullable=False)
    rank: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        index=True,
        nullable=False,
    )

    score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        index=True,
        nullable=False,
    )
    match_score: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    combined_score: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    semantic_score: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    keyword_score: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )

    verdict: Mapped[str] = mapped_column(
        String(100),
        default="",
        server_default=text("''"),
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(
        Text,
        default="",
        server_default=text("''"),
        nullable=False,
    )

    matched_skills: Mapped[str] = mapped_column(
        Text,
        default=EMPTY_JSON_LIST,
        server_default=text("'[]'"),
        nullable=False,
    )
    missing_skills: Mapped[str] = mapped_column(
        Text,
        default=EMPTY_JSON_LIST,
        server_default=text("'[]'"),
        nullable=False,
    )
    recommendations: Mapped[str] = mapped_column(
        Text,
        default=EMPTY_JSON_LIST,
        server_default=text("'[]'"),
        nullable=False,
    )
    matched_keywords: Mapped[str] = mapped_column(
        Text,
        default=EMPTY_JSON_LIST,
        server_default=text("'[]'"),
        nullable=False,
    )
    missing_keywords: Mapped[str] = mapped_column(
        Text,
        default=EMPTY_JSON_LIST,
        server_default=text("'[]'"),
        nullable=False,
    )

    favorite: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=DEFAULT_CANDIDATE_STATUS,
        server_default=text("'new'"),
        index=True,
        nullable=False,
    )
    notes: Mapped[str] = mapped_column(
        Text,
        default="",
        server_default=text("''"),
        nullable=False,
    )
    tags: Mapped[str] = mapped_column(
        Text,
        default=EMPTY_JSON_LIST,
        server_default=text("'[]'"),
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(100),
        default=DEFAULT_CANDIDATE_SOURCE,
        server_default=text("'recruiter_mode'"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="recruiter_candidates",
    )

    def __repr__(self) -> str:
        return (
            f"RecruiterCandidate(id={self.id!r}, user_id={self.user_id!r}, "
            f"status={self.status!r}, score={self.score!r}, "
            f"favorite={self.favorite!r})"
        )


class RecruiterJob(Base):
    """Persist a resumable Recruiter Mode batch job and its progress."""

    __tablename__ = "recruiter_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=DEFAULT_RECRUITER_JOB_STATUS,
        server_default=text("'queued'"),
        index=True,
        nullable=False,
    )
    progress: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    total_candidates: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    processed_candidates: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    job_description: Mapped[str] = mapped_column(Text, nullable=False)
    input_payload: Mapped[str] = mapped_column(Text, nullable=False)
    result_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="recruiter_jobs")

    def __repr__(self) -> str:
        return (
            f"RecruiterJob(job_id={self.job_id!r}, user_id={self.user_id!r}, "
            f"status={self.status!r}, progress={self.progress!r})"
        )
