import json
import os
import re
import ssl
from io import BytesIO

import certifi
from dotenv import load_dotenv
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

ssl._create_default_https_context = ssl.create_default_context(
    cafile=certifi.where()
)

from auth import get_current_user, get_test_user
from billing import (
    create_checkout_url,
    verify_webhook_signature,
)
from db import Base, engine, get_db
from models import AnalysisRecord, User
from openai_service import (
    analyze_cv_with_ai,
    rewrite_cv_with_ai,
)
from pdf_report import build_analysis_pdf_report
from pdf_utils import extract_text_from_pdf
from schemas import (
    AnalysisResponse,
    BillingCheckoutResponse,
    HistoryItemResponse,
)
from storage import upload_pdf_to_firebase
from usage_service import (
    ensure_analysis_allowed,
    get_user_usage,
)

load_dotenv()

Base.metadata.create_all(bind=engine)


def run_lightweight_migrations() -> None:
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    ALTER TABLE users
                    ADD COLUMN analyses_used INTEGER DEFAULT 0
                    """
                )
            )
    except Exception:
        pass


run_lightweight_migrations()

app = FastAPI(title="TalentMatch Pro API")

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        (
            "http://localhost:8501,"
            "http://127.0.0.1:8501,"
            "https://talentmatch-frontend-dejan.onrender.com"
        ),
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
        "database_configured": bool(
            os.getenv("DATABASE_URL", "").strip()
        ),
        "openai_configured": bool(
            os.getenv("OPENAI_API_KEY", "").strip()
        ),
        "firebase_project_configured": bool(
            os.getenv("FIREBASE_PROJECT_ID", "").strip()
        ),
        "firebase_storage_configured": bool(
            os.getenv("FIREBASE_STORAGE_BUCKET", "").strip()
        ),
    }


def parse_json_list(value: str) -> list[str]:
    try:
        data = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    return [
        str(item).strip()
        for item in data
        if str(item).strip()
    ]


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


@app.get("/me")
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    usage = get_user_usage(
        db,
        current_user,
    )

    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "plan": current_user.plan,
        "is_pro": current_user.is_pro,
        **usage,
    }


@app.post(
    "/analyze-resume",
    response_model=AnalysisResponse,
)
async def analyze_resume(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_analysis_allowed(
        db,
        current_user,
    )

    pdf_bytes = await file.read()

    if not pdf_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded PDF is empty.",
        )

    try:
        cv_text = extract_text_from_pdf(pdf_bytes)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not extract text: {exc}",
        )

    if not cv_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Could not extract text from PDF.",
        )

    try:
        result = analyze_cv_with_ai(
            cv_text,
            job_description,
        )
    except Exception as exc:
        print("OPENAI ERROR:", exc)

        raise HTTPException(
            status_code=500,
            detail=f"AI analysis failed: {exc}",
        )

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
        cv_storage_path=storage_path,
        job_description=job_description,
        score=result["score"],
        summary=result["summary"],
        matched_skills=json.dumps(
            result["strengths"]
        ),
        missing_skills=json.dumps(
            result["weaknesses"]
        ),
        recommendations=json.dumps(
            result["recommendations"]
        ),
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    get_user_usage(
        db,
        current_user,
    )

    result["storage_path"] = storage_path

    return result


@app.post("/billing/create-checkout")
def create_checkout(
    current_user: User = Depends(get_current_user),
):
    return {
        "checkout_url": create_checkout_url(
            email=current_user.email,
            user_id=current_user.id,
        )
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
        "is_pro": current_user.is_pro,
    }


@app.post("/billing/webhook")
async def webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    body = await request.body()

    signature = request.headers.get(
        "X-Signature",
        "",
    )

    if not verify_webhook_signature(
        body,
        signature,
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid webhook signature.",
        )

    payload = await request.json()

    meta = payload.get("meta", {}) or {}
    custom_data = (
        meta.get("custom_data", {}) or {}
    )

    user_id = custom_data.get("user_id")

    if not user_id:
        return {
            "status": "ignored",
            "reason": "Missing user_id",
        }

    user = (
        db.query(User)
        .filter(User.id == int(user_id))
        .first()
    )

    if not user:
        return {
            "status": "ignored",
            "reason": "User not found",
        }

    user.plan = "pro"
    user.is_pro = True

    db.add(user)
    db.commit()

    return {
        "status": "ok",
        "upgraded_user_id": user.id,
    }