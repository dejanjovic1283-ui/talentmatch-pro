import csv
import json
from io import BytesIO, StringIO

import streamlit as st

from auth_utils import api_get, is_logged_in


st.set_page_config(page_title="History • TalentMatch Pro", page_icon="📜", layout="wide")

st.title("📜 Analysis History")
st.caption("View your previous CV analyses and reports.")


TYPE_LABELS = {
    "cv_analysis": "CV Analysis",
    "ats_checker": "ATS",
    "ats": "ATS",
    "semantic_match": "Semantic",
    "recruiter_mode": "Recruiter",
}

FILTER_OPTIONS = {
    "All": None,
    "ATS": "ats_checker",
    "Semantic": "semantic_match",
    "Recruiter": "recruiter_mode",
    "CV Analysis": "cv_analysis",
}


def safe_list(value):
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []

        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except Exception:
            pass

        return [item.strip() for item in raw.split(",") if item.strip()]

    return [str(value).strip()] if str(value).strip() else []


def history_label(item: dict) -> str:
    analysis_type = str(item.get("analysis_type") or "cv_analysis").strip().lower()
    return TYPE_LABELS.get(analysis_type, analysis_type.replace("_", " ").title())


def normalize_type(item: dict) -> str:
    return str(item.get("analysis_type") or "cv_analysis").strip().lower()


def parse_history_response(response):
    status_code = getattr(response, "status_code", None)
    text = getattr(response, "text", "") or ""
    headers = getattr(response, "headers", {}) or {}
    content_type = headers.get("content-type", "")

    if status_code != 200:
        try:
            payload = response.json()
            detail = payload.get("detail") or payload.get("error") or payload
            return None, f"Failed to load history: {status_code} - {detail}"
        except Exception:
            return None, f"Failed to load history: {status_code} - {text[:1000]}"

    if content_type and "application/json" not in content_type:
        return None, f"Backend returned non-JSON response: {text[:1000]}"

    try:
        payload = response.json()
    except Exception:
        return None, f"Backend returned invalid JSON: {text[:1000]}"

    if isinstance(payload, list):
        return payload, None

    if isinstance(payload, dict):
        items = payload.get("items") or payload.get("history") or payload.get("data") or []
        if isinstance(items, list):
            return items, None

    return None, "Backend returned invalid history format."


def make_csv(items: list[dict]) -> bytes:
    output = StringIO()
    fieldnames = [
        "created_at",
        "analysis_type",
        "cv_filename",
        "score",
        "summary",
        "matched_skills",
        "missing_skills",
        "recommendations",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for item in items:
        writer.writerow(
            {
                "created_at": item.get("created_at") or item.get("date") or "",
                "analysis_type": history_label(item),
                "cv_filename": item.get("cv_filename") or item.get("filename") or "",
                "score": item.get("score") or item.get("match_score") or 0,
                "summary": item.get("summary") or "",
                "matched_skills": ", ".join(
                    safe_list(item.get("matched_skills") or item.get("strengths") or item.get("matched_keywords"))
                ),
                "missing_skills": ", ".join(
                    safe_list(item.get("missing_skills") or item.get("weaknesses") or item.get("missing_keywords"))
                ),
                "recommendations": " | ".join(safe_list(item.get("recommendations"))),
            }
        )

    return output.getvalue().encode("utf-8-sig")


def make_pdf(items: list[dict]) -> bytes | None:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    except Exception:
        return None

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="TalentMatch Pro History")
    styles = getSampleStyleSheet()

    story = [
        Paragraph("TalentMatch Pro - Analysis History", styles["Title"]),
        Spacer(1, 12),
    ]

    if not items:
        story.append(Paragraph("No history records found.", styles["BodyText"]))
    else:
        for idx, item in enumerate(items, start=1):
            cv_file = item.get("cv_filename") or item.get("filename") or "CV"
            score = item.get("score") or item.get("match_score") or 0
            created_at = item.get("created_at") or item.get("date") or ""