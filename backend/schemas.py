from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserProfileResponse(BaseModel):
    """Payload returned by the profile endpoint."""

    id: int
    email: EmailStr
    full_name: str | None = None
    plan: str
    is_pro: bool


class AnalysisResponse(BaseModel):
    """Canonical AI analysis response used by the frontend."""

    score: int
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]


class HistoryItemResponse(BaseModel):
    """History item returned to the frontend."""

    id: int
    cv_filename: str | None = None
    cv_storage_path: str | None = None
    job_description: str
    score: int
    summary: str
    matched_skills: list[str]
    missing_skills: list[str]
    recommendations: list[str]
    created_at: datetime


class BillingCheckoutResponse(BaseModel):
    """Checkout URL payload."""

    checkout_url: str
