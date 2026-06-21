import json
import os
import re
import ssl
import csv
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any

import certifi
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, Response, StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
ssl._create_default_https_context = ssl.create_default_context(cafile=certifi.where())

load_dotenv()

from auth import get_current_user, get_test_user
from billing.factory import get_billing_provider
from db import Base, engine, get_db
from models import AnalysisRecord, User
from openai_service import AIServiceError, analyze_cv_with_ai, rewrite_cv_with_ai
from pdf_report import build_analysis_pdf_report
from pdf_utils import extract_text_from_pdf
from recruiter_service import rank_candidates
from schemas import AnalysisResponse, HistoryItemResponse
from semantic_service import analyze_semantic_match
from storage import upload_pdf_to_firebase
from usage_service import ensure_analysis_allowed, get_user_usage


Base.metadata.create_all(bind=engine)


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


def run_lightweight_migrations() -> None:
    migrations = [
        "ALTER TABLE users ADD COLUMN analyses_used INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN plan VARCHAR DEFAULT 'free'",
        "ALTER TABLE users ADD COLUMN is_pro BOOLEAN DEFAULT 0",
        "ALTER TABLE users ADD COLUMN paypal_customer_id VARCHAR",
        "ALTER TABLE users ADD COLUMN paypal_subscription_id VARCHAR",
        "ALTER TABLE users ADD COLUMN paypal_subscription_status VARCHAR",
        "ALTER TABLE analysis_records ADD COLUMN analysis_type VARCHAR DEFAULT 'cv_analysis'",
    ]

    for migration in migrations:
        try:
            with engine.begin() as conn:
                conn.execute(text(migration))
        except Exception:
            pass


run_lightweight_migrations()

app = FastAPI(title="TalentMatch Pro API", version="0.1.0")


def get_cors_origins() -> list[str]:
    raw = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8501,http://127.0.0.1:8501,https://talentmatch-frontend-dejan.onrender.com",
    )
    return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "PAYPAL-TRANSMISSION-ID",
        "PAYPAL-TRANSMISSION-TIME",
        "PAYPAL-CERT-URL",
        "PAYPAL-AUTH-ALGO",
        "PAYPAL-TRANSMISSION-SIG",
    ],
)



def no_download_headers(content_type: str) -> dict[str, str]:
    return {
        "Content-Type": content_type,
        "Content-Disposition": "inline",
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "X-Content-Type-Options": "nosniff",
        "X-Robots-Tag": "all",
    }


def config_status() -> dict:
    database_url = os.getenv("DATABASE_URL", "").strip()
    firebase_credentials = os.getenv("FIREBASE_CREDENTIALS", "").strip()
    google_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()

    return {
        "environment": os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development")),
        "database_configured": bool(database_url),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY", "").strip()),
        "firebase_project_configured": bool(os.getenv("FIREBASE_PROJECT_ID", "").strip()),
        "firebase_storage_configured": bool(os.getenv("FIREBASE_STORAGE_BUCKET", "").strip()),
        "firebase_credentials_configured": bool(firebase_credentials or google_credentials),
        "billing_provider": os.getenv("BILLING_PROVIDER", "paypal"),
        "paypal_client_configured": bool(os.getenv("PAYPAL_CLIENT_ID", "").strip()),
        "paypal_secret_configured": bool(os.getenv("PAYPAL_CLIENT_SECRET", "").strip()),
        "paypal_plan_configured": bool(os.getenv("PAYPAL_PLAN_ID", "").strip()),
        "paypal_webhook_configured": bool(os.getenv("PAYPAL_WEBHOOK_ID", "").strip()),
        "paypal_environment": os.getenv("PAYPAL_ENV", "live"),
        "frontend_url_configured": bool(os.getenv("FRONTEND_URL", "").strip()),
        "cors_origins_count": len(get_cors_origins()),
    }


def parse_json_list(value: str) -> list[str]:
    try:
        data = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    return [str(item).strip() for item in data if str(item).strip()]


def raise_ai_http_exception(exc: AIServiceError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={
            "message": exc.message,
            "type": "ai_service_error",
        },
    )


def save_history_record(
    db: Session,
    user: User,
    cv_filename: str | None,
    job_description: str,
    score: int,
    summary: str,
    matched: list[str] | None = None,
    missing: list[str] | None = None,
    recommendations: list[str] | None = None,
    cv_storage_path: str | None = None,
    analysis_type: str = "cv_analysis",
) -> AnalysisRecord:
    """Save any successful analysis-like result so the History page can display it."""
    record = AnalysisRecord(
        user_id=user.id,
        cv_filename=cv_filename or "resume.pdf",
        cv_storage_path=cv_storage_path,
        job_description=job_description,
        score=int(score or 0),
        summary=summary or "",
        matched_skills=json.dumps(matched or []),
        missing_skills=json.dumps(missing or []),
        recommendations=json.dumps(recommendations or []),
        analysis_type=analysis_type,
    )

    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def score_verdict(score: int, strong_label: str = "Strong Match", good_label: str = "Good Match", weak_label: str = "Weak Match") -> str:
    if score >= 80:
        return strong_label
    if score >= 60:
        return good_label
    return weak_label


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "TalentMatch Pro backend running.",
        **config_status(),
    }


@app.get("/robots.txt", include_in_schema=False)
def robots_txt():
    """Public robots.txt used by Google Search Console."""
    robots_content = """User-agent: *
Allow: /

Sitemap: https://talentmatchcv.com/sitemap.xml
"""

    return PlainTextResponse(
        content=robots_content,
        media_type="text/plain; charset=utf-8",
        headers=no_download_headers("text/plain; charset=utf-8"),
    )


@app.head("/robots.txt", include_in_schema=False)
def robots_txt_head():
    return Response(
        status_code=200,
        media_type="text/plain; charset=utf-8",
        headers=no_download_headers("text/plain; charset=utf-8"),
    )


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap_xml():
    """Public XML sitemap used by Google Search Console."""
    sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">

  <url>
    <loc>https://talentmatchcv.com/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>

  <url>
    <loc>https://talentmatchcv.com/pricing</loc>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>

  <url>
    <loc>https://talentmatchcv.com/privacy</loc>
    <changefreq>yearly</changefreq>
    <priority>0.6</priority>
  </url>

  <url>
    <loc>https://talentmatchcv.com/terms</loc>
    <changefreq>yearly</changefreq>
    <priority>0.6</priority>
  </url>

  <url>
    <loc>https://talentmatchcv.com/refund</loc>
    <changefreq>yearly</changefreq>
    <priority>0.6</priority>
  </url>

</urlset>
"""

    return Response(
        content=sitemap_content,
        media_type="application/xml; charset=utf-8",
        headers=no_download_headers("application/xml; charset=utf-8"),
    )


@app.head("/sitemap.xml", include_in_schema=False)
def sitemap_xml_head():
    return Response(
        status_code=200,
        media_type="application/xml; charset=utf-8",
        headers=no_download_headers("application/xml; charset=utf-8"),
    )


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

    status = "ready" if checks["database_connection_ok"] else "not_ready"
    return {"status": status, **checks}


@app.get("/me")
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.expire_all()
    user = db.query(User).filter(User.id == current_user.id).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    usage = get_user_usage(db, user)

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "plan": user.plan,
        "is_pro": bool(user.is_pro),
        "paypal_customer_id": getattr(user, "paypal_customer_id", None),
        "paypal_subscription_id": getattr(user, "paypal_subscription_id", None),
        "paypal_subscription_status": getattr(user, "paypal_subscription_status", None),
        **usage,
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

    result = None
    try:
        result = analyze_cv_with_ai(cv_text, job_description)
    except AIServiceError as exc:
        print("OPENAI ANALYSIS ERROR:", repr(exc))
        raise_ai_http_exception(exc)

    try:
        storage_path = upload_pdf_to_firebase(
            pdf_bytes,
            current_user.id,
            file.filename or "resume.pdf",
        )
    except Exception as exc:
        print("FIREBASE STORAGE ERROR:", repr(exc))
        storage_path = None

    if result is None:
        raise HTTPException(status_code=502, detail="AI analysis returned no result.")

    save_history_record(
        db=db,
        user=current_user,
        cv_filename=file.filename,
        cv_storage_path=storage_path,
        job_description=job_description,
        score=result["score"],
        summary=result["summary"],
        matched=result["strengths"],
        missing=result["weaknesses"],
        recommendations=result["recommendations"],
        analysis_type="cv_analysis",
    )

    get_user_usage(db, current_user)

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
        return analyze_cv_with_ai(cv_text, job_description)
    except AIServiceError as exc:
        print("OPENAI ANALYSIS TEST ERROR:", repr(exc))
        raise_ai_http_exception(exc)


ATS_STOPWORDS = {
    "and", "or", "the", "a", "an", "to", "of", "for", "in", "on", "with",
    "as", "is", "are", "be", "by", "this", "that", "you", "your", "we",
    "our", "will", "from", "at", "it", "their", "they", "them",
    "role", "candidate", "candidates", "experience", "skills",
    "strong", "work", "working", "build", "building", "product",
    "products", "what", "have", "has", "about", "into", "against",
    "real", "helps", "using", "job", "jobs", "description",
    "descriptions", "identify", "compare", "platform",
    "founding", "full", "stack", "fullstack", "full-stack",
    "pro", "seekers", "team", "looking", "years", "required",
    "preferred", "talentmatch", "cv", "resume", "engineer",
    "modern", "increase", "chances", "optimize", "powered",
    "analysis", "application", "strategy", "ship", "own", "gaps",
    "improve", "scale", "integrate", "integration", "integrations",
    "workflow", "workflows", "seeker", "company", "companies",
    "startup", "startups", "founder", "owning", "shipping",
    "improving", "scaling", "good", "great", "excellent",
    "need", "needs", "needed", "want", "wants", "ability",
    "able", "must", "should", "could", "would", "high", "value",
    "plus", "bonus", "fast", "paced", "environment",
}


def extract_ats_keywords(text_value: str, limit: int = 30) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{2,}", text_value.lower())
    keywords = []

    for word in words:
        clean = word.strip(".,:;()[]{}")
        if clean and clean not in ATS_STOPWORDS and clean not in keywords:
            keywords.append(clean)

    priority_terms = [
        "python", "fastapi", "sql", "postgresql", "api", "apis", "docker",
        "firebase", "openai", "saas", "backend", "frontend", "streamlit",
        "auth", "authentication", "storage", "billing", "deployment",
        "cloud", "pdf", "ai", "prompt", "database", "render", "mvp",
        "ats", "recruiter", "paypal", "postgres",
        "javascript", "typescript", "react", "rest",
    ]

    ordered = []

    for term in priority_terms:
        if term in keywords and term not in ordered:
            ordered.append(term)

    for keyword in keywords:
        if keyword not in ordered:
            ordered.append(keyword)

    return ordered[:limit]


@app.post("/ats-test")
async def ats_test(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    verdict = "ATS Strong" if coverage >= 80 else "ATS Good" if coverage >= 60 else "ATS Weak"
    recommendations = [
        f"Add missing high-value keywords where truthful: {', '.join(missing[:8])}."
        if missing
        else "Your CV covers the main ATS keywords well.",
        "Mirror important job-description terms naturally in your CV summary and experience bullets.",
        "Use exact tool names where relevant, for example FastAPI, Docker, SQL, Firebase, OpenAI.",
    ]

    save_history_record(
        db=db,
        user=current_user,
        cv_filename=file.filename,
        job_description=job_description,
        score=coverage,
        summary=f"ATS keyword check completed. Coverage: {coverage}%. Verdict: {verdict}.",
        matched=matched,
        missing=missing,
        recommendations=recommendations,
        analysis_type="ats_checker",
    )

    get_user_usage(db, current_user)

    return {
        "score": coverage,
        "coverage": coverage,
        "verdict": verdict,
        "total_keywords": len(keywords),
        "matched_keywords": matched,
        "missing_keywords": missing,
        "recommendations": recommendations,
    }


@app.post("/ats-check")
async def ats_check(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ats_test(file=file, job_description=job_description, db=db, current_user=current_user)


@app.post("/semantic-match")
async def semantic_match(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_pro:
        raise HTTPException(status_code=403, detail="Semantic matching is a Pro feature.")

    pdf_bytes = await file.read()

    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")

    try:
        cv_text = extract_text_from_pdf(pdf_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not extract text from PDF: {exc}")

    result: dict[str, Any] = {}
    try:
        result = analyze_semantic_match(cv_text, job_description)
    except AIServiceError as exc:
        print("SEMANTIC MATCH AI ERROR:", repr(exc))
        raise_ai_http_exception(exc)
    except Exception as exc:
        print("SEMANTIC MATCH ERROR:", repr(exc))
        raise HTTPException(status_code=500, detail=f"Semantic match failed: {exc}")

    score = int(result.get("combined_score", result.get("score", 0)) or 0)
    summary = result.get("summary") or result.get("recruiter_summary") or f"Semantic match completed. Score: {score}/100."
    matched = result.get("matched_themes") or result.get("matched_keywords") or result.get("strengths") or []
    missing = result.get("missing_themes") or result.get("missing_keywords") or result.get("weaknesses") or []
    recommendations = result.get("recommendations") or []

    save_history_record(
        db=db,
        user=current_user,
        cv_filename=file.filename,
        job_description=job_description,
        score=score,
        summary=summary,
        matched=matched,
        missing=missing,
        recommendations=recommendations,
        analysis_type="semantic_match",
    )

    return result


@app.post("/recruiter/rank-candidates")
async def recruiter_rank_candidates(
    files: list[UploadFile] = File(...),
    job_description: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_pro:
        raise HTTPException(status_code=403, detail="Recruiter Mode is a Pro feature.")

    if not files:
        raise HTTPException(status_code=400, detail="Please upload at least one CV.")

    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 CV files allowed per ranking run.")

    candidates = []

    for uploaded_file in files:
        pdf_bytes = await uploaded_file.read()

        try:
            cv_text = extract_text_from_pdf(pdf_bytes) if pdf_bytes else ""
        except Exception as exc:
            print(f"CV EXTRACT ERROR for {uploaded_file.filename}:", repr(exc))
            cv_text = ""
     