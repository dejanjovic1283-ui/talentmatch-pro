from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


Identifier = Annotated[int, Field(gt=0)]
Score = Annotated[int, Field(ge=0, le=100)]
NonNegativeInt = Annotated[int, Field(ge=0)]
PositiveCount = Annotated[int, Field(ge=1)]
Percentage = Annotated[float, Field(ge=0.0, le=100.0)]
MoneyUSD = Annotated[float, Field(ge=0.0)]
ShortText = Annotated[str, Field(max_length=255)]
NonEmptyText = Annotated[str, Field(min_length=1)]


class APIResponseModel(BaseModel):
    """
    Shared configuration for TalentMatch Pro API response schemas.

    The schemas remain backward-compatible with the existing API payloads
    while supporting validation from SQLAlchemy objects under Pydantic v2.
    Unknown fields are ignored deliberately so response serialization does
    not break when internal ORM or service objects gain additional fields.
    """

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class UserProfileResponse(APIResponseModel):
    """Payload returned by the authenticated user profile endpoint."""

    id: Identifier
    email: EmailStr
    full_name: ShortText | None = None

    plan: Annotated[str, Field(min_length=1, max_length=50)]
    is_pro: bool
    is_admin: bool = False

    paypal_customer_id: ShortText | None = None
    paypal_subscription_id: ShortText | None = None
    paypal_subscription_status: Annotated[
        str,
        Field(max_length=100),
    ] | None = None


class AnalysisResponse(APIResponseModel):
    """Canonical AI analysis response consumed by the frontend."""

    score: Score
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]

    @field_validator(
        "strengths",
        "weaknesses",
        "recommendations",
        mode="before",
    )
    @classmethod
    def normalize_string_lists(cls, value: object) -> object:
        """
        Normalize nullable list payloads without changing the public contract.

        AI and legacy service layers occasionally produce ``None`` for an
        empty collection. The API contract consistently exposes JSON arrays.
        """
        return [] if value is None else value


class HistoryItemResponse(APIResponseModel):
    """History item returned to the frontend."""

    id: Identifier
    analysis_type: Annotated[str, Field(min_length=1, max_length=50)] = "cv_analysis"
    cv_filename: ShortText | None = None
    cv_storage_path: Annotated[str, Field(max_length=500)] | None = None
    job_description: NonEmptyText
    score: Score
    summary: str
    matched_skills: list[str]
    missing_skills: list[str]
    recommendations: list[str]
    created_at: datetime

    @field_validator(
        "matched_skills",
        "missing_skills",
        "recommendations",
        mode="before",
    )
    @classmethod
    def normalize_history_lists(cls, value: object) -> object:
        """Expose absent collection values as stable JSON arrays."""
        return [] if value is None else value

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        """
        Normalize timestamps to timezone-aware UTC.

        SQLite can return naive datetimes during local development, while
        PostgreSQL returns timezone-aware values in production.
        """
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class BillingCheckoutResponse(APIResponseModel):
    """PayPal checkout URL payload."""

    checkout_url: AnyHttpUrl


class RecruiterJobCreateResponse(APIResponseModel):
    """Acknowledgement returned when a recruiter batch job is queued."""

    job_id: Annotated[str, Field(min_length=36, max_length=36)]
    status: Annotated[str, Field(min_length=1, max_length=32)]
    progress: Annotated[int, Field(ge=0, le=100)] = 0
    total_candidates: Annotated[int, Field(ge=1, le=1000)]
    processed_candidates: Annotated[int, Field(ge=0)] = 0


class RecruiterJobStatusResponse(RecruiterJobCreateResponse):
    """Current state and optional result of a recruiter batch job."""

    result: dict | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime


class AdminAnalyticsUserMetrics(APIResponseModel):
    """User, plan, and conversion metrics for the administrator dashboard."""

    total_users: NonNegativeInt
    free_users: NonNegativeInt
    active_pro_users: NonNegativeInt
    paid_subscribers: NonNegativeInt
    pro_conversion_rate: Percentage


class AdminAnalyticsAnalysisMetrics(APIResponseModel):
    """Product usage and score-quality metrics for persisted analyses."""

    total_analyses: NonNegativeInt
    scored_analyses: NonNegativeInt
    average_score: Percentage
    strong_matches: NonNegativeInt
    competitive_matches: NonNegativeInt
    needs_work_matches: NonNegativeInt


class AdminAnalyticsMixMetrics(APIResponseModel):
    """Persisted analysis counts grouped by production analysis type."""

    cv_analysis: NonNegativeInt = 0
    ats_checker: NonNegativeInt = 0
    semantic_match: NonNegativeInt = 0
    recruiter_mode: NonNegativeInt = 0
    cv_rewrite: NonNegativeInt = 0
    other: NonNegativeInt = 0


class AdminAnalyticsMissingSkill(APIResponseModel):
    """One normalized missing-skill frequency entry."""

    name: Annotated[str, Field(min_length=1, max_length=255)]
    count: PositiveCount


class AdminAnalyticsBillingMetrics(APIResponseModel):
    """
    Current PayPal-derived subscription estimate.

    This is intentionally named estimated MRR rather than recognized revenue
    because TalentMatch Pro does not persist a payment-ledger history.
    """

    pro_price_usd: MoneyUSD
    estimated_mrr_usd: MoneyUSD


class AdminAnalyticsResponse(APIResponseModel):
    """Canonical response payload for the administrator analytics endpoint."""

    generated_at: datetime
    users: AdminAnalyticsUserMetrics
    analyses: AdminAnalyticsAnalysisMetrics
    analysis_mix: AdminAnalyticsMixMetrics
    top_missing_skills: list[AdminAnalyticsMissingSkill]
    billing: AdminAnalyticsBillingMetrics

    @field_validator("generated_at")
    @classmethod
    def normalize_generated_at(cls, value: datetime) -> datetime:
        """Expose the analytics snapshot timestamp as timezone-aware UTC."""
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
