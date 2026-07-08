from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


class User(Base):
    """Application user synced from Firebase authentication."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    firebase_uid: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    plan: Mapped[str] = mapped_column(String(50), default="free")
    is_pro: Mapped[bool] = mapped_column(Boolean, default=False)
    analyses_used: Mapped[int] = mapped_column(Integer, default=0)

    # PayPal billing fields
    paypal_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    paypal_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    paypal_subscription_status: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    analyses = relationship("AnalysisRecord", back_populates="user")
    recruiter_candidates = relationship(
        "RecruiterCandidate",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class AnalysisRecord(Base):
    """Stores each CV analysis result for history and plan limits."""

    __tablename__ = "analysis_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    cv_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cv_storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    job_description: Mapped[str] = mapped_column(Text)
    score: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str] = mapped_column(Text, default="")
    matched_skills: Mapped[str] = mapped_column(Text, default="[]")
    missing_skills: Mapped[str] = mapped_column(Text, default="[]")
    recommendations: Mapped[str] = mapped_column(Text, default="[]")
    analysis_type: Mapped[str] = mapped_column(String(50), default="cv_analysis", index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="analyses")


class RecruiterCandidate(Base):
    """
    Stores individual candidates produced by Recruiter Mode.

    This is the foundation for TalentMatch Pro v2.0 Recruiter Workspace:
    - Candidate Database
    - Favorites
    - Tags
    - Recruiter Notes
    - Job Projects
    - Candidate filtering and dashboards
    """

    __tablename__ = "recruiter_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    filename: Mapped[str] = mapped_column(String(255), index=True)
    cv_storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    job_description: Mapped[str] = mapped_column(Text)
    rank: Mapped[int] = mapped_column(Integer, default=0, index=True)

    score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    match_score: Mapped[int] = mapped_column(Integer, default=0)
    combined_score: Mapped[int] = mapped_column(Integer, default=0)
    semantic_score: Mapped[int] = mapped_column(Integer, default=0)
    keyword_score: Mapped[int] = mapped_column(Integer, default=0)

    verdict: Mapped[str] = mapped_column(String(100), default="")
    summary: Mapped[str] = mapped_column(Text, default="")

    matched_skills: Mapped[str] = mapped_column(Text, default="[]")
    missing_skills: Mapped[str] = mapped_column(Text, default="[]")
    recommendations: Mapped[str] = mapped_column(Text, default="[]")
    matched_keywords: Mapped[str] = mapped_column(Text, default="[]")
    missing_keywords: Mapped[str] = mapped_column(Text, default="[]")

    favorite: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="new", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[str] = mapped_column(Text, default="[]")

    source: Mapped[str] = mapped_column(String(100), default="recruiter_mode")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    user = relationship("User", back_populates="recruiter_candidates")