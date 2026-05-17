import json
import os
import re
import ssl
from io import BytesIO

import certifi
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
ssl._create_default_https_context = ssl.create_default_context(cafile=certifi.where())

from auth import get_current_user, get_test_user
from db import Base, engine, get_db
from models import AnalysisRecord, User
from openai_service import analyze_cv_with_ai, rewrite_cv_with_ai
from pdf_report import build_analysis_pdf_report
from pdf_utils import extract_text_from_pdf
from recruiter_service import rank_candidates
from schemas import AnalysisResponse, HistoryItemResponse
from semantic_service import analyze_semantic_match
from storage import upload_pdf_to_firebase
from stripe_billing import (
    create_checkout_session,
    create_customer_portal_url,
    handle_stripe_webhook,
)
from usage_service import ensure_analysis_allowed, get_user_usage

load_dotenv()

Base.metadata.create_all(bind=engine)


def run_lightweight_migrations() -> None:
    migrations = [
        "ALTER TABLE users ADD COLUMN analyses_used INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN plan VARCHAR DEFAULT 'free'",
        "ALTER TABLE users ADD COLUMN is_pro BOOLEAN DEFAULT 0",
    ]

    for migration in migrations:
        try:
            with engine.begin() as conn:
                conn.execute(text(migration))
        except Exception:
            pass


run_lightweight_migrations()

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


def config_status() -> dict:
    return {
        "database_configured": bool(os.getenv("DATABASE_URL", "").strip()),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY", "").strip()),
        "firebase_project_configured": bool(os.getenv("FIREBASE_PROJECT_ID", "").strip()),
        "firebase_storage_configured": bool(os.getenv("FIREBASE_STORAGE_BUCKET", "").strip()),
        "stripe_secret_configured": bool(os.getenv("STRIPE_SECRET_KEY", "").strip()),
        "stripe_price_configured": bool(os.getenv("STRIPE_PRICE_ID", "").strip()),
        "stripe_webhook_configured": bool(os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()),
    }


def parse_json_list(value: str) -> list[str]:
    try:
        data = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    return [str(item).strip() for item in data if str(item).strip()]


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "TalentMatch Pro backend running.",
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

    try:
        result = analyze_cv_with_ai(cv_text, job_description)
    except Exception as exc:
        print("OPENAI ANALYSIS ERROR:", repr(exc))
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {exc}")

    try:
        storage_path = upload_pdf_to_firebase(
            pdf_bytes,
            current_user.id,
            file.filename or "resume.pdf",
        )
    except Exception as exc:
        print("FIREBASE STORAGE ERROR:", repr(exc))
        storage_path = None

    record = AnalysisRecord(
        user_id=current_user.id,
        cv_filename=file.filename,
        cv_storage_path=storage_path,
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

    get_user_usage(db, current_user)

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
        print("OPENAI ANALYSIS TEST ERROR:", repr(exc))
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {exc}")

    result["storage_path"] = None
    return result


ATS_STOPWORDS = {
    "and", "or", "the", "a", "an", "to", "of", "for", "in", "on", "with",
    "as", "is", "are", "be", "by", "this", "that", "you", "your", "we",
    "our", "will", "from", "at", "it", "their", "they", "them", "role",
    "candidate", "experience", "skills", "strong", "work", "working",
    "build", "building", "product", "what", "have", "has", "about",
    "into", "against", "real", "helps", "using",
}


def extract_ats_keywords(text_value: str, limit: int = 30) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{2,}", text_value.lower())
    keywords = []

    for word in words:
        clean = word.strip(".,:;()[]{}")
        if clean and clean not in ATS_STOPWORDS and clean not in keywords:
            keywords.append(clean)

    priority_terms = [
        "python", "fastapi", "sql", "api", "apis", "docker", "firebase",
        "openai", "saas", "backend", "frontend", "streamlit", "auth",
        "authentication", "storage", "billing", "deployment", "cloud",
        "pdf", "ai", "prompt", "database", "render", "mvp", "ats",
        "recruiter",
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
            if missing
            else "Your CV covers the main ATS keywords well.",
            "Mirror important job-description terms naturally in your CV summary and experience bullets.",
            "Use exact tool names where relevant, for example FastAPI, Docker, SQL, Firebase, OpenAI.",
        ],
    }


@app.post("/semantic-match")
async def semantic_match(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_pro:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Semantic matching is a Pro feature.",
                "upgrade_required": True,
                "plan": current_user.plan,
                "is_pro": current_user.is_pro,
            },
        )

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
        return analyze_semantic_match(cv_text, job_description)
    except Exception as exc:
        print("SEMANTIC MATCH ERROR:", repr(exc))
        raise HTTPException(status_code=500, detail=f"Semantic match failed: {exc}")


@app.post("/recruiter/rank-candidates")
async def recruiter_rank_candidates(
    files: list[UploadFile] = File(...),
    job_description: str = Form(...),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_pro:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Recruiter Mode is a Pro feature.",
                "upgrade_required": True,
                "plan": current_user.plan,
                "is_pro": current_user.is_pro,
            },
        )

    if not files:
        raise HTTPException(status_code=400, detail="Please upload at least one CV.")

    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 CV files allowed per ranking run.")

    candidates = []

    for uploaded_file in files:
        pdf_bytes = await uploaded_file.read()

        if not pdf_bytes:
            candidates.append(
                {
                    "filename": uploaded_file.filename or "candidate.pdf",
                    "cv_text": "",
                }
            )
            continue

        try:
            cv_text = extract_text_from_pdf(pdf_bytes)
        except Exception as exc:
            print(f"CV EXTRACT ERROR for {uploaded_file.filename}:", repr(exc))
            cv_text = ""

        candidates.append(
            {
                "filename": uploaded_file.filename or "candidate.pdf",
                "cv_text": cv_text,
            }
        )

    try:
        return rank_candidates(
            candidates=candidates,
            job_description=job_description,
        )
    except Exception as exc:
        print("RECRUITER RANKING ERROR:", repr(exc))
        raise HTTPException(status_code=500, detail=f"Recruiter ranking failed: {exc}")


@app.post("/rewrite-cv")
async def rewrite_cv(
    file: UploadFile = File(...),
    job_description: str = Form(...),
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

    if not current_user.is_pro:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "CV Rewrite AI is a Pro feature.",
                "upgrade_required": True,
                "plan": current_user.plan,
                "is_pro": current_user.is_pro,
            },
        )

    try:
        return rewrite_cv_with_ai(cv_text, job_description)
    except Exception as exc:
        print("OPENAI CV REWRITE ERROR:", repr(exc))
        raise HTTPException(status_code=500, detail=f"CV rewrite failed: {exc}")


@app.post("/reports/analysis-pdf")
async def create_analysis_pdf_report(
    cv_filename: str = Form(...),
    score: int = Form(...),
    summary: str = Form(...),
    strengths_json: str = Form("[]"),
    weaknesses_json: str = Form("[]"),
    recommendations_json: str = Form("[]"),
    job_description: str = Form(""),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_pro:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "PDF reports are a Pro feature.",
                "upgrade_required": True,
                "plan": current_user.plan,
                "is_pro": current_user.is_pro,
            },
        )

    strengths = parse_json_list(strengths_json)
    weaknesses = parse_json_list(weaknesses_json)
    recommendations = parse_json_list(recommendations_json)

    try:
        pdf_bytes = build_analysis_pdf_report(
            cv_filename=cv_filename,
            score=score,
            summary=summary,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            job_description=job_description,
        )
    except Exception as exc:
        print("PDF REPORT ERROR:", repr(exc))
        raise HTTPException(status_code=500, detail=f"PDF report failed: {exc}")

    safe_filename = re.sub(r"[^a-zA-Z0-9_-]+", "_", cv_filename.replace(".pdf", ""))
    download_name = f"{safe_filename}_talentmatch_report.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
    )


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
        }
    ]


@app.post("/billing/create-checkout")
def create_checkout(current_user: User = Depends(get_current_user)):
    return {
        "checkout_url": create_checkout_session(current_user)
    }


@app.post("/billing/create-portal")
def create_portal(current_user: User = Depends(get_current_user)):
    return {
        "portal_url": create_customer_portal_url(current_user)
    }


@app.post("/billing/demo-upgrade")
def demo_upgrade_to_pro(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.plan = "pro"
    current_user.is_pro = True

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return {
        "status": "ok",
        "message": "Demo upgrade successful.",
        "plan": current_user.plan,
        "is_pro": bool(current_user.is_pro),
    }


@app.post("/billing/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        body = await request.body()
        signature = request.headers.get("stripe-signature", "")

        print("=== STRIPE WEBHOOK RECEIVED ===")
        print("SIGNATURE PRESENT:", bool(signature))

        result = handle_stripe_webhook(
            body=body,
            signature=signature,
            db=db,
        )

        print("WEBHOOK RESULT:", result)

        return {
            "received": True,
            "result": result,
        }

    except Exception as exc:
        print("WEBHOOK FATAL ERROR:", repr(exc))
        db.rollback()

        return {
            "received": False,
            "error": str(exc),
        }