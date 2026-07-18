from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
import streamlit as st

from auth_utils import is_logged_in, is_pro_user
from components.sidebar import render_sidebar
from components.ui import apply_global_styles, render_hero, safe_html


LOGGER = logging.getLogger(__name__)
BACKEND_URL = os.getenv("BACKEND_URL", "https://api.talentmatchcv.com").rstrip("/")
REQUEST_TIMEOUT_SECONDS = 120
PDF_TIMEOUT_SECONDS = 120
MAX_JOB_DESCRIPTION_CHARACTERS = 15_000
MAX_SUMMARY_CHARACTERS = 4_000
MAX_LIST_ITEMS = 40
MAX_LIST_ITEM_CHARACTERS = 500

st.set_page_config(page_title="CV Analysis • TalentMatch Pro", page_icon="📄", layout="wide")
apply_global_styles()
render_sidebar()


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def api_url(path: str) -> str:
    clean_path = path if path.startswith("/") else f"/{path}"
    return f"{BACKEND_URL}{clean_path}"


def clean_text(value: Any, *, max_chars: int = MAX_SUMMARY_CHARACTERS) -> str:
    text = str(value or "")
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) > max_chars:
        return text[: max_chars - 1].rstrip() + "…"
    return text


def normalize_list(
    value: Any,
    *,
    max_items: int = MAX_LIST_ITEMS,
    max_item_chars: int = MAX_LIST_ITEM_CHARACTERS,
) -> List[str]:
    if value is None:
        return []

    raw_items: Iterable[Any]
    if isinstance(value, (list, tuple, set)):
        raw_items = value
    elif isinstance(value, str):
        raw_items = re.split(r"[\n,;]+", value)
    else:
        raw_items = [value]

    result: List[str] = []
    seen: set[str] = set()
    for item in raw_items:
        if isinstance(item, (dict, list, tuple, set)):
            continue
        normalized = clean_text(item, max_chars=max_item_chars)
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
        if len(result) >= max_items:
            break
    return result


def score_number(value: Any) -> int:
    if value is None or isinstance(value, bool):
        return 0
    try:
        if isinstance(value, (int, float)):
            numeric = float(value)
        elif isinstance(value, str):
            match = re.search(r"-?\d+(?:[.,]\d+)?", value)
            if match is None:
                return 0
            numeric = float(match.group(0).replace(",", "."))
        else:
            return 0
        if 0 < numeric <= 1:
            numeric *= 100
        return max(0, min(100, int(round(numeric))))
    except (TypeError, ValueError, OverflowError):
        return 0


def get_result_score(result: Dict[str, Any]) -> int:
    for key in (
        "score",
        "overall_score",
        "match_score",
        "analysis_score",
        "cv_score",
        "compatibility_score",
    ):
        score = score_number(result.get(key))
        if score > 0:
            return score
    return 0


def get_auth_headers() -> Dict[str, str]:
    token = (
        st.session_state.get("access_token")
        or st.session_state.get("id_token")
        or st.session_state.get("firebase_id_token")
        or st.session_state.get("auth_token")
        or st.session_state.get("token")
    )
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def extract_error_message(response: requests.Response) -> str:
    default = f"Backend returned HTTP {response.status_code}."
    try:
        payload = response.json()
    except (TypeError, ValueError, json.JSONDecodeError):
        payload = None
    if isinstance(payload, dict):
        detail = payload.get("detail") or payload.get("message") or payload.get("error")
        if detail:
            return clean_text(detail, max_chars=500)
    return default


def normalize_analysis_result(payload: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return None
    return {
        **payload,
        "score": get_result_score(payload),
        "summary": clean_text(
            payload.get("summary")
            or payload.get("analysis")
            or payload.get("executive_summary")
            or "",
            max_chars=MAX_SUMMARY_CHARACTERS,
        ),
        "strengths": normalize_list(
            payload.get("strengths")
            or payload.get("matched_skills")
            or payload.get("matched_keywords")
        ),
        "weaknesses": normalize_list(
            payload.get("weaknesses")
            or payload.get("missing_skills")
            or payload.get("gaps")
        ),
        "recommendations": normalize_list(payload.get("recommendations")),
    }


def build_text_report(result: Dict[str, Any], cv_filename: str, job_description: str) -> str:
    normalized = normalize_analysis_result(result) or {}
    score = score_number(normalized.get("score"))
    summary = clean_text(normalized.get("summary"), max_chars=MAX_SUMMARY_CHARACTERS)
    strengths = normalize_list(normalized.get("strengths"))
    weaknesses = normalize_list(normalized.get("weaknesses"))
    recommendations = normalize_list(normalized.get("recommendations"))
    job_description_clean = clean_text(job_description, max_chars=MAX_JOB_DESCRIPTION_CHARACTERS)

    lines = [
        "TalentMatch Pro - CV Analysis Report",
        "=" * 42,
        f"Generated: {utc_timestamp()}",
        f"CV file: {clean_text(cv_filename, max_chars=200)}",
        f"Score: {score}/100",
        "",
        "Executive Summary",
        "-" * 24,
        summary or "No summary returned.",
        "",
        "Strengths",
        "-" * 20,
    ]
    lines.extend([f"- {item}" for item in strengths] or ["- No strengths returned."])
    lines.extend(["", "Weaknesses / Gaps", "-" * 20])
    lines.extend([f"- {item}" for item in weaknesses] or ["- No weaknesses returned."])
    lines.extend(["", "Priority Recommendations", "-" * 28])
    lines.extend(
        [f"{index}. {item}" for index, item in enumerate(recommendations, 1)]
        or ["1. No recommendations returned."]
    )
    if job_description_clean:
        lines.extend(["", "Job Description Appendix", "-" * 26, job_description_clean])
    return "\n".join(lines)


def create_pdf_report(
    result: Dict[str, Any],
    cv_filename: str,
    job_description: str,
) -> Optional[bytes]:
    normalized = normalize_analysis_result(result) or {}
    data = {
        "cv_filename": clean_text(cv_filename, max_chars=200),
        "score": str(score_number(normalized.get("score"))),
        "summary": clean_text(normalized.get("summary"), max_chars=MAX_SUMMARY_CHARACTERS),
        "strengths_json": json.dumps(normalize_list(normalized.get("strengths")), ensure_ascii=False),
        "weaknesses_json": json.dumps(normalize_list(normalized.get("weaknesses")), ensure_ascii=False),
        "recommendations_json": json.dumps(
            normalize_list(normalized.get("recommendations")), ensure_ascii=False
        ),
        "job_description": clean_text(
            job_description, max_chars=MAX_JOB_DESCRIPTION_CHARACTERS
        ),
    }

    try:
        response = requests.post(
            api_url("/reports/analysis-pdf"),
            headers=get_auth_headers(),
            data=data,
            timeout=PDF_TIMEOUT_SECONDS,
        )
        if response.status_code == 401:
            st.error("Your session expired. Please log in again before generating the PDF.")
            return None
        if response.status_code == 403:
            st.warning("PDF Report is available in Pro.")
            st.page_link("pages/pricing.py", label="💳 Upgrade to Pro")
            return None
        if response.status_code >= 400:
            LOGGER.warning(
                "CV Analysis PDF request failed.",
                extra={"event": "cv_analysis_pdf_request_failed", "status_code": response.status_code},
            )
            st.error("PDF report could not be generated. " + extract_error_message(response))
            return None

        content_type = response.headers.get("content-type", "").lower()
        if "application/pdf" not in content_type:
            LOGGER.error(
                "CV Analysis PDF endpoint returned unexpected content type.",
                extra={
                    "event": "cv_analysis_pdf_invalid_content_type",
                    "content_type": content_type,
                },
            )
            st.error("Backend returned an invalid PDF response.")
            return None
        if not response.content.startswith(b"%PDF"):
            LOGGER.error(
                "CV Analysis PDF payload is invalid.",
                extra={"event": "cv_analysis_pdf_invalid_payload"},
            )
            st.error("Generated PDF payload is invalid.")
            return None
        return response.content
    except requests.exceptions.Timeout:
        st.error("PDF report timed out. Please try again.")
        return None
    except requests.exceptions.RequestException as exc:
        LOGGER.warning(
            "CV Analysis PDF request failed.",
            extra={
                "event": "cv_analysis_pdf_request_exception",
                "error_type": type(exc).__name__,
            },
        )
        st.error("PDF report could not reach the backend. Please try again.")
        return None
    except Exception as exc:
        LOGGER.exception(
            "Unexpected CV Analysis PDF failure.",
            extra={
                "event": "cv_analysis_pdf_unexpected_failure",
                "error_type": type(exc).__name__,
            },
        )
        st.error("PDF report could not be generated.")
        return None


def analyze_resume(uploaded_file: Any, job_description: str) -> Optional[Dict[str, Any]]:
    safe_filename = clean_text(uploaded_file.name, max_chars=200)
    media_type = clean_text(uploaded_file.type or "application/pdf", max_chars=100)
    files = {
        "file": (
            safe_filename,
            uploaded_file.getvalue(),
            media_type,
        )
    }
    data = {
        "job_description": clean_text(
            job_description, max_chars=MAX_JOB_DESCRIPTION_CHARACTERS
        )
    }

    try:
        response = requests.post(
            api_url("/analyze-resume"),
            headers=get_auth_headers(),
            files=files,
            data=data,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code == 401:
            st.error("Your session expired. Please log in again before running CV Analysis.")
            return None
        if response.status_code == 403:
            st.error("CV Analysis is blocked by backend permissions.")
            return None
        if response.status_code == 429:
            st.error("Too many requests. Please wait and try again.")
            return None
        if response.status_code >= 400:
            LOGGER.warning(
                "CV Analysis request failed.",
                extra={"event": "cv_analysis_request_failed", "status_code": response.status_code},
            )
            st.error("CV Analysis failed. " + extract_error_message(response))
            return None
        try:
            payload = response.json()
        except (TypeError, ValueError, json.JSONDecodeError):
            st.error("Backend returned an invalid response.")
            return None
        normalized = normalize_analysis_result(payload)
        if normalized is None:
            st.error("Backend response is not a valid analysis object.")
            return None
        return normalized
    except requests.exceptions.Timeout:
        st.error(
            "CV Analysis timed out. Please try again with a shorter CV or job description."
        )
        return None
    except requests.exceptions.RequestException as exc:
        LOGGER.warning(
            "CV Analysis request could not reach backend.",
            extra={
                "event": "cv_analysis_request_exception",
                "error_type": type(exc).__name__,
            },
        )
        st.error("CV Analysis could not reach the backend. Please try again.")
        return None
    except Exception as exc:
        LOGGER.exception(
            "Unexpected CV Analysis failure.",
            extra={
                "event": "cv_analysis_unexpected_failure",
                "error_type": type(exc).__name__,
            },
        )
        st.error("CV Analysis failed unexpectedly.")
        return None


def clear_cv_analysis_state() -> None:
    for key in (
        "cv_analysis_result",
        "cv_analysis_filename",
        "cv_analysis_job_description",
        "cv_analysis_txt_report",
        "cv_analysis_pdf_report",
    ):
        st.session_state.pop(key, None)


def score_tone(score: int) -> Tuple[str, str]:
    if score >= 80:
        return "#059669", "Strong match"
    if score >= 60:
        return "#2563EB", "Competitive"
    if score >= 40:
        return "#D97706", "Needs improvement"
    return "#DC2626", "Low match"


def render_kpi_card(label: str, value: str, caption: str, accent: str) -> None:
    st.markdown(
        f"""
        <div class="tm-card" style="border-top:4px solid {safe_html(accent)};min-height:160px;display:flex;flex-direction:column;justify-content:space-between;">
            <div class="tm-kicker">{safe_html(label)}</div>
            <div style="font-size:2.2rem;font-weight:800;line-height:1;color:#0F172A;margin:.55rem 0;">{safe_html(value)}</div>
            <div class="tm-muted">{safe_html(caption)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_list_card(title: str, icon: str, items: List[str], *, positive: bool = False) -> None:
    if items:
        badge_class = "tm-pill tm-pill-green" if positive else "tm-pill"
        content = "".join(
            f"<span class='{badge_class}'>{safe_html(item)}</span>" for item in items
        )
    else:
        content = "<div class='tm-muted'>No items returned.</div>"
    st.markdown(
        f"""
        <div class="tm-card" style="min-height:220px">
            <div class="tm-card-title">{safe_html(icon)} {safe_html(title)}</div>
            <div style="margin-top:.8rem">{content}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_analysis_result(
    result: Dict[str, Any],
    cv_filename: str,
    job_description: str,
) -> None:
    normalized = normalize_analysis_result(result) or {}
    score = score_number(normalized.get("score"))
    summary = clean_text(normalized.get("summary"), max_chars=MAX_SUMMARY_CHARACTERS)
    strengths = normalize_list(normalized.get("strengths"))
    weaknesses = normalize_list(normalized.get("weaknesses"))
    recommendations = normalize_list(normalized.get("recommendations"))
    accent, verdict = score_tone(score)

    st.success("CV Analysis completed successfully and saved to History.")
    st.markdown('<div class="tm-section-title">Analysis Intelligence</div>', unsafe_allow_html=True)
    kpi_1, kpi_2, kpi_3, kpi_4 = st.columns(4)
    with kpi_1:
        render_kpi_card("Overall Score", f"{score}/100", verdict, accent)
    with kpi_2:
        render_kpi_card("Strengths", str(len(strengths)), "Confirmed candidate advantages", "#059669")
    with kpi_3:
        render_kpi_card("Gaps", str(len(weaknesses)), "Areas requiring attention", "#D97706")
    with kpi_4:
        render_kpi_card("Actions", str(len(recommendations)), "Priority recommendations", "#2563EB")

    st.markdown(
        f"""
        <div class="tm-card" style="margin-top:.8rem">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:1rem;flex-wrap:wrap;">
                <div><div class="tm-kicker">Overall CV alignment</div><div class="tm-card-title" style="margin-top:.25rem">{safe_html(verdict)}</div></div>
                <div style="font-weight:800;color:{safe_html(accent)}">{score}/100</div>
            </div>
            <div style="width:100%;height:14px;margin-top:1rem;border-radius:999px;background:#E2E8F0;overflow:hidden;">
                <div style="width:{score}%;height:100%;background:{safe_html(accent)};border-radius:999px;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="tm-section-title">Executive Summary</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="tm-card" style="border-left:5px solid #2563EB;padding:1.35rem 1.5rem;">
            <div class="tm-kicker">Recruiter perspective</div>
            <div style="margin-top:.55rem;line-height:1.7;color:#475569;font-size:1rem;">{safe_html(summary or 'No summary returned.')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="tm-section-title">CV Coverage</div>', unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        render_list_card("Strengths", "✅", strengths, positive=True)
    with right:
        render_list_card("Weaknesses / Gaps", "⚠️", weaknesses)

    st.markdown('<div class="tm-section-title">Priority Recommendations</div>', unsafe_allow_html=True)
    if recommendations:
        for index, recommendation in enumerate(recommendations, start=1):
            st.markdown(
                f"""
                <div class="tm-card" style="margin-bottom:.75rem;display:grid;grid-template-columns:54px 1fr;gap:1rem;align-items:start;">
                    <div style="width:42px;height:42px;border-radius:12px;display:flex;align-items:center;justify-content:center;background:#EFF6FF;color:#2563EB;font-weight:800;">{index}</div>
                    <div><div class="tm-kicker">Priority {index}</div><div class="tm-muted" style="margin-top:.25rem">{safe_html(recommendation)}</div></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("No recommendations returned.")

    if "cv_analysis_txt_report" not in st.session_state:
        st.session_state["cv_analysis_txt_report"] = build_text_report(
            result=normalized,
            cv_filename=cv_filename,
            job_description=job_description,
        )

    st.markdown("---")
    st.markdown('<div class="tm-section-title">Download Report</div>', unsafe_allow_html=True)
    st.caption(
        "Exports include the score, executive summary, strengths, gaps, recommendations and a bounded Job Description appendix."
    )
    col_txt, col_pdf = st.columns(2)
    with col_txt:
        st.download_button(
            label="⬇️ Export CV Analysis Report (.txt)",
            data=st.session_state["cv_analysis_txt_report"].encode("utf-8"),
            file_name="talentmatch_cv_analysis_report.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with col_pdf:
        if is_pro_user():
            if "cv_analysis_pdf_report" not in st.session_state:
                with st.spinner("Preparing PDF report..."):
                    st.session_state["cv_analysis_pdf_report"] = create_pdf_report(
                        result=normalized,
                        cv_filename=cv_filename,
                        job_description=job_description,
                    )
            pdf_bytes = st.session_state.get("cv_analysis_pdf_report")
            if pdf_bytes:
                st.download_button(
                    label="📄 Export CV Analysis Report (.pdf)",
                    data=pdf_bytes,
                    file_name="talentmatch_cv_analysis_report.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
        else:
            st.info("PDF Report is available in Pro.")
            st.page_link("pages/pricing.py", label="💳 Upgrade to Pro")


render_hero(
    "AI CV INTELLIGENCE",
    "CV Analysis",
    "Evaluate role alignment, candidate strengths, gaps and practical improvement priorities.",
    "📄",
)

if not is_logged_in():
    st.warning("Please log in to use CV Analysis.")
    st.page_link("pages/login.py", label="🔐 Go to Login")
    st.stop()

st.markdown('<div class="tm-section-title">Run a new CV analysis</div>', unsafe_allow_html=True)
left, right = st.columns([1, 1.25])
with left:
    st.markdown(
        """
        <div class="tm-card"><div class="tm-card-title">📄 CV upload</div><div class="tm-muted">Upload one PDF CV. TalentMatch Pro analyses role fit, strengths, gaps and improvement opportunities.</div></div>
        """,
        unsafe_allow_html=True,
    )
    uploaded_file = st.file_uploader(
        "Upload CV PDF",
        type=["pdf"],
        accept_multiple_files=False,
        help="Upload one PDF CV or resume.",
    )
    if uploaded_file is not None:
        safe_filename = clean_text(uploaded_file.name, max_chars=200)
        st.success(f"Selected file: {safe_filename} ({uploaded_file.size / 1024:.1f} KB)")

with right:
    st.markdown(
        """
        <div class="tm-card"><div class="tm-card-title">🧾 Job description</div><div class="tm-muted">Paste the complete job advertisement for the most accurate role-fit analysis and recommendation quality.</div></div>
        """,
        unsafe_allow_html=True,
    )
    job_description = st.text_area(
        "Paste job description",
        height=330,
        max_chars=MAX_JOB_DESCRIPTION_CHARACTERS,
        placeholder="Paste the full job description here...",
    )

analyze_clicked = st.button(
    "🚀 Analyze CV",
    type="primary",
    use_container_width=True,
    disabled=uploaded_file is None or not job_description.strip(),
)

if analyze_clicked:
    if uploaded_file is None:
        st.error("Please upload a PDF CV first.")
        st.stop()
    job_description_clean = clean_text(
        job_description,
        max_chars=MAX_JOB_DESCRIPTION_CHARACTERS,
    )
    if not job_description_clean:
        st.error("Please paste a job description first.")
        st.stop()
    clear_cv_analysis_state()
    with st.spinner("Analyzing CV with AI..."):
        result = analyze_resume(uploaded_file, job_description_clean)
    if result:
        st.session_state["cv_analysis_result"] = result
        st.session_state["cv_analysis_filename"] = clean_text(uploaded_file.name, max_chars=200)
        st.session_state["cv_analysis_job_description"] = job_description_clean

stored_result = st.session_state.get("cv_analysis_result")
if isinstance(stored_result, dict):
    render_analysis_result(
        result=stored_result,
        cv_filename=clean_text(
            st.session_state.get("cv_analysis_filename", "uploaded_cv.pdf"),
            max_chars=200,
        ),
        job_description=clean_text(
            st.session_state.get("cv_analysis_job_description", ""),
            max_chars=MAX_JOB_DESCRIPTION_CHARACTERS,
        ),
    )
