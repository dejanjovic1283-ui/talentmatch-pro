import json
import os
import ssl

import certifi
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

# Make certificate handling explicit for Windows-friendly local development.
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
ssl._create_default_https_context = ssl.create_default_context(cafile=certifi.where())

from auth import get_current_user, get_test_user
from billing import create_checkout_url, verify_webhook_signature
from db import Base, engine, get_db
from models import AnalysisRecord, User
from openai_service import analyze_cv_with_ai
from pdf_utils import extract_text_from_pdf
from schemas import (
    AnalysisResponse,
    BillingCheckoutResponse,
    HistoryItemResponse,
    UserProfileResponse,
)
from storage import upload_pdf_to_firebase

# Load environment variables and create database tables on startup.
load_dotenv()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="TalentMatch Pro API")

# Use explicit origins because credentialed requests should not use wildcard CORS.
allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

FREE_PLAN_ANALYSIS_LIMIT = int(os.getenv("FREE_PLAN_ANALYSIS_LIMIT", "3"))


def ensure_analysis_allowed(db: Session, user: User) -> None:
    """Enforce the free-plan usage limit before running AI analysis."""
    if user.is_pro:
        return

    used = db.query(AnalysisRecord).filter(AnalysisRecord.user_id == user.id).count()
    if used >= FREE_PLAN_ANALYSIS_LIMIT:
        raise HTTPException(
            status_code=403,
            detail=f"Free plan limit reached ({FREE_PLAN_ANALYSIS_LIMIT}). Please upgrade to Pro.",
        )


def config_status() -> dict:
    """Return high-level configuration status for debugging and health checks."""
    return {
        "database_configured": bool(os.getenv("DATABASE_URL", "").strip()),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY", "").strip()),
        "firebase_project_configured": bool(os.getenv("FIREBASE_PROJECT_ID", "").strip()),
        "firebase_credentials_configured": bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()),
        "firebase_storage_configured": bool(os.getenv("FIREBASE_STORAGE_BUCKET", "").strip()),
        "lemonsqueezy_checkout_configured": bool(os.getenv("LEMON_SQUEEZY_CHECKOUT_URL", "").strip()),
        "lemonsqueezy_webhook_configured": bool(os.getenv("LEMON_SQUEEZY_WEBHOOK_SECRET", "").strip()),
    }


@app.get("/")
def root():
    """Simple root endpoint for smoke testing."""
    return {
        "status": "ok",
        "message": "TalentMatch Pro backend is running.",
        **config_status(),
    }


@app.get("/healthz")
def healthz():
    """Liveness probe endpoint."""
    return {"status": "ok"}


@app.get("/readyz")
def readyz(db: Session = Depends(get_db)):
    """Readiness probe endpoint that checks dependencies and configuration."""
    checks = config_status()

    try:
        db.execute(text("SELECT 1"))
        checks["database_connection_ok"] = True
    except Exception:
        checks["database_connection_ok"] = False

    ready = all(
        [
            checks["database_connection_ok"],
            checks["openai_configured"],
            checks["firebase_project_configured"],
            checks["firebase_credentials_configured"],
            checks["firebase_storage_configured"],
        ]
    )

    if not ready:
        raise HTTPException(status_code=503, detail=checks)

    return {"status": "ready", **checks}


@app.get("/me", response_model=UserProfileResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    """Return the current authenticated user profile."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "plan": current_user.plan,
        "is_pro": current_user.is_pro,
    }


@app.post("/analyze-resume", response_model=AnalysisResponse)
async def analyze_resume(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Analyze a CV against a job description and store the results."""
    ensure_analysis_allowed(db, current_user)

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")

    try:
        cv_text = extract_text_from_pdf(pdf_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not extract text from PDF: {exc}")

    if not cv_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from PDF.")

    try:
        result = analyze_cv_with_ai(cv_text, job_description)
    except Exception as exc:
        print("OPENAI ANALYSIS ERROR:", exc)
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {exc}")

    try:
        storage_path = upload_pdf_to_firebase(
            pdf_bytes,
            current_user.id,
            file.filename or "resume.pdf",
        )
    except Exception as exc:
        print("FIREBASE STORAGE ERROR:", exc)
        raise HTTPException(status_code=500, detail=f"Firebase Storage upload failed: {exc}")

    record = AnalysisRecord(
        user_id=current_user.id,
        cv_filename=file.filename,
        cv_storage_path=storage_path or None,
        job_description=job_description,
        score=result["score"],
        summary=result["summary"],
        matched_skills=json.dumps(result["strengths"]),
        missing_skills=json.dumps(result["weaknesses"]),
        recommendations=json.dumps(result["recommendations"]),
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return result


@app.post("/analyze-test", response_model=AnalysisResponse)
async def analyze_test(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    current_user: User = Depends(get_test_user),
):
    """Analyze a CV locally without Firebase Auth. Development only."""

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")

    try:
        cv_text = extract_text_from_pdf(pdf_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not extract text from PDF: {exc}")

    if not cv_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from PDF.")

    try:
        result = analyze_cv_with_ai(cv_text, job_description)
    except Exception as exc:
        print("OPENAI ANALYSIS TEST ERROR:", exc)
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {exc}")

    try:
        storage_path = upload_pdf_to_firebase(
            pdf_bytes,
            1,
            file.filename or "test_cv.pdf",
        )
    except Exception as exc:
        print("FIREBASE STORAGE TEST ERROR:", exc)
        raise HTTPException(status_code=500, detail=f"Firebase Storage upload failed: {exc}")

    result["storage_path"] = storage_path

    return result


@app.get("/history", response_model=list[HistoryItemResponse])
def get_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the current user's previous CV analyses."""
    records = (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.user_id == current_user.id)
        .order_by(AnalysisRecord.created_at.desc())
        .all()
    )

    return [
        {
            "id": record.id,
            "cv_filename": record.cv_filename,
            "cv_storage_path": record.cv_storage_path,
            "job_description": record.job_description,
            "score": record.score,
            "summary": record.summary,
            "matched_skills": json.loads(record.matched_skills or "[]"),
            "missing_skills": json.loads(record.missing_skills or "[]"),
            "recommendations": json.loads(record.recommendations or "[]"),
            "created_at": record.created_at,
        }
        for record in records
    ]


@app.post("/billing/create-checkout", response_model=BillingCheckoutResponse)
def create_checkout(current_user: User = Depends(get_current_user)):
    """Generate a checkout URL that is linked to the signed-in user."""
    return {
        "checkout_url": create_checkout_url(
            email=current_user.email,
            user_id=current_user.id,
        )
    }


@app.post("/billing/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    """Process Lemon Squeezy webhooks and upgrade local users to Pro."""
    body = await request.body()
    signature = request.headers.get("X-Signature", "")

    if not verify_webhook_signature(body, signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")

    payload = await request.json()

    meta = payload.get("meta", {}) or {}
    event_name = meta.get("event_name", "")
    custom_data = meta.get("custom_data", {}) or {}
    attributes = payload.get("data", {}).get("attributes", {}) or {}

    paid_status = str(attributes.get("status", "")).lower()
    if event_name and paid_status and paid_status not in {"paid", "active", "on_trial"}:
        return {"status": "ignored", "event_name": event_name, "payment_status": paid_status}

    user_id = custom_data.get("user_id")
    email = custom_data.get("email") or attributes.get("user_email")

    user = None
    if user_id:
        try:
            user = db.query(User).filter(User.id == int(user_id)).first()
        except ValueError:
            user = None

    if user is None and email:
        user = db.query(User).filter(User.email == email).first()

    if user:
        user.plan = "pro"
        user.is_pro = True
        db.commit()
        return {"status": "ok", "upgraded_user_id": user.id}

    return {"status": "ok", "upgraded_user_id": None}
