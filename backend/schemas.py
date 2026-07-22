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
    total_candidates: Annotated[int, Field(ge=1, le=100)]
    processed_candidates: Annotated[int, Field(ge=0)] = 0


class RecruiterJobStatusResponse(RecruiterJobCreateResponse):
    """Current state and optional result of a recruiter batch job."""

    result: dict | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime
