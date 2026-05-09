import json
import os
import re
import ssl

import certifi
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

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

load_dotenv()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="TalentMatch Pro API")

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8501,http://127.0.0.1:8501,https://talentmatch-frontend-dejan.onrender.com",
    ).split(",")
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
    if user.is_pro:
        return

    used = db.query(AnalysisRecord).filter(AnalysisRecord.user_id == user.id).count()
    if used >= FREE_PLAN_ANALYSIS_LIMIT:
        raise HTTPException(
            status_code=403,
            detail=f"Free plan limit reached ({FREE_PLAN_ANALYSIS_LIMIT}). Please upgrade to Pro.",
        )


def config_status() -> dict:
    return {
        "database_configured": bool(os.getenv("DATABASE_URL", "").strip()),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY", "").strip()),
        "firebase_project_configured": bool(os.getenv("FIREBASE_PROJECT_ID", "").strip()),
        "firebase_credentials_configured": bool(
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
            or os.getenv("FIREBASE_CREDENTIALS", "").strip()
        ),
        "firebase_storage_configured": bool(os.getenv("FIREBASE_STORAGE_BUCKET", "").strip()),
        "lemonsqueezy_checkout_configured": bool(os.getenv("LEMON_SQUEEZY_CHECKOUT_URL", "").strip()),
        "lemonsqueezy_webhook_configured": bool(os.getenv("LEMON_SQUEEZY_WEBHOOK_SECRET", "").strip()),
    }


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "TalentMatch Pro backend is running.",
        **config_status(),
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz(db: Session = Depends(get_db)):
    checks = config_status()

    try:
        db.execute(text("SELECT 1"))
        checks["database_connection_ok"] = True
    except Exception:
        checks["database_connection_ok"] = False

    return {"status": "ready", **checks}


@app.get("/me", response_model=UserProfileResponse)
def get_profile(current_user: User = Depends(get_current_user)):
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
        storage_path = None

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

    result["storage_path"] = storage_path
    return result


@app.post("/analyze-test", response_model=AnalysisResponse)
async def analyze_test(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    current_user: User = Depends(get_test_user),
):
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

    result["storage_path"] = None
    return result


ATS_STOPWORDS = {
    "and", "or", "the", "a", "an", "to", "of", "for", "in", "on", "with", "as",
    "is", "are", "be", "by", "this", "that", "you", "your", "we", "our", "will",
    "from", "at", "it", "their", "they", "them", "role", "candidate", "experience",
    "skills", "strong", "work", "working", "build", "building", "product", "what",
    "have", "has", "about", "into", "against", "real", "helps", "helps", "using",
}


def extract_ats_keywords(text: str, limit: int = 30) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{2,}", text.lower())

    keywords = []
    for word in words:
        clean = word.strip(".,:;()[]{}")
        if clean and clean not in ATS_STOPWORDS and clean not in keywords:
            keywords.append(clean)

    priority_terms = [
        "python", "fastapi", "sql", "api", "apis", "docker", "firebase",
        "openai", "saas", "backend", "frontend", "streamlit", "auth",
        "authentication", "storage", "billing", "lemon", "squeezy",
        "deployment", "cloud", "pdf", "ai", "prompt", "database",
        "render", "mvp", "ats", "recruiter",
    ]

    ordered = []
    for term in priority_terms:
        if term in keywords:
            ordered.append(term)

    for keyword in keywords:
        if keyword not in ordered:
            ordered.append(keyword)

    return ordered[:limit]


@app.post("/ats-test")
async def ats_test(
    file: UploadFile = File(...),
    job_description: str = Form(...),
):
    pdf_bytes = await file.read()

    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")

    try:
        cv_text = extract_text_from_pdf(pdf_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not extract text from PDF: {exc}")

    if not cv_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from PDF.")

    keywords = extract_ats_keywords(job_description)
    cv_lower = cv_text.lower()

    matched = []
    missing = []

    for keyword in keywords:
        if keyword.lower() in cv_lower:
            matched.append(keyword)
        else:
            missing.append(keyword)

    coverage = round((len(matched) / len(keywords)) * 100) if keywords else 0

    if coverage >= 80:
        verdict = "ATS Strong"
    elif coverage >= 60:
        verdict = "ATS Good"
    else:
        verdict = "ATS Weak"

    return {
        "coverage": coverage,
        "verdict": verdict,
        "total_keywords": len(keywords),
        "matched_keywords": matched,
        "missing_keywords": missing,
        "recommendations": [
            f"Add missing high-value keywords where truthful: {', '.join(missing[:8])}."
            if missing else "Your CV covers the main ATS keywords well.",
            "Mirror important job-description terms naturally in your CV summary and experience bullets.",
            "Use exact tool names where relevant, for example FastAPI, Docker, SQL, Firebase, OpenAI.",
        ],
    }


@app.get("/history", response_model=list[HistoryItemResponse])
def get_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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


@app.get("/history-test")
def get_history_test():
    return [
        {
            "id": 1,
            "cv_filename": "20260501_cv1.pdf",
            "cv_storage_path": None,
            "job_description": "Founding Full-Stack AI SaaS Engineer",
            "score": 55,
            "summary": "John Doe has foundational Python backend skills but lacks depth in SaaS integrations, Docker, billing workflows, and AI product experience.",
            "matched_skills": [
                "Basic Python backend knowledge",
                "REST API exposure",
                "Motivated junior developer profile",
            ],
            "missing_skills": [
                "Limited FastAPI production experience",
                "No clear SaaS billing workflow experience",
                "Limited AI product experience",
            ],
            "recommendations": [
                "Highlight any FastAPI projects.",
                "Add examples of API integrations.",
                "Mention deployment or Docker experience if available.",
            ],
            "created_at": "2026-05-03T08:00:00",
        },
        {
            "id": 2,
            "cv_filename": "20260501_cv2.pdf",
            "cv_storage_path": None,
            "job_description": "Founding Full-Stack AI SaaS Engineer",
            "score": 85,
            "summary": "Jane Smith is a strong match with backend engineering, FastAPI, Firebase, Docker, and SaaS-oriented experience.",
            "matched_skills": [
                "Strong Python backend fundamentals",
                "Experience with FastAPI and REST APIs",
                "Integrated Firebase authentication and storage",
                "Experience with Docker for deployment",
            ],
            "missing_skills": [
                "Limited explicit Lemon Squeezy billing experience",
                "Could mention more AI product work",
            ],
            "recommendations": [
                "Add billing workflow experience.",
                "Highlight AI product ownership.",
                "Mention prompt design or PDF processing experience.",
            ],
            "created_at": "2026-05-03T08:10:00",
        },
        {
            "id": 3,
            "cv_filename": "20260501_cv3.pdf",
            "cv_storage_path": None,
            "job_description": "Founding Full-Stack AI SaaS Engineer",
            "score": 85,
            "summary": "Alex Morgan has strong Python, FastAPI, Docker, and AI product alignment, with minor gaps around billing and deployment pipeline ownership.",
            "matched_skills": [
                "Python and FastAPI experience",
                "Docker deployment familiarity",
                "AI product and document processing exposure",
                "Backend API development",
            ],
            "missing_skills": [
                "No direct Lemon Squeezy billing example",
                "Limited deployment pipeline ownership details",
            ],
            "recommendations": [
                "Add examples of cloud deployment ownership.",
                "Mention payment or subscription integrations.",
                "Emphasize end-to-end SaaS MVP delivery.",
            ],
            "created_at": "2026-05-03T08:20:00",
        },
    ]


@app.post("/billing/create-checkout", response_model=BillingCheckoutResponse)
def create_checkout(current_user: User = Depends(get_current_user)):
    return {
        "checkout_url": create_checkout_url(
            email=current_user.email,
            user_id=current_user.id,
        )
    }


@app.post("/billing/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
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