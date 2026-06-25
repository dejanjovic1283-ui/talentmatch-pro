import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

import requests
import streamlit as st

from auth_utils import is_logged_in, is_pro_user


BACKEND_URL = os.getenv("BACKEND_URL", "https://api.talentmatchcv.com").rstrip("/")


def api_url(path: str) -> str:
    clean_path = path if path.startswith("/") else f"/{path}"
    return f"{BACKEND_URL}{clean_path}"


def get_auth_headers() -> Dict[str, str]:
    token = st.session_state.get("access_token") or st.session_state.get("token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def normalize_list(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item) for item in value if item is not None]

    if isinstance(value, str):
        parts = [part.strip() for part in value.replace("\n", ",").split(",")]
        return [part for part in parts if part]

    return [str(value)]


def build_text_report(
    result: Dict[str, Any],
    cv_filename: str,
    job_description: str,
) -> str:
    score = result.get("score", 0)
    summary = result.get("summary") or result.get("analysis") or ""
    strengths = normalize_list(result.get("strengths") or result.get("matched_skills"))
    weaknesses = normalize_list(result.get("weaknesses") or result.get("missing_skills"))
    recommendations = normalize_list(result.get("recommendations"))

    lines = [
        "TalentMatch Pro - CV Analysis Report",
        "=" * 42,
        f"Generated: {datetime.utcnow().isoformat()} UTC",
        f"CV file: {cv_filename}",
        f"Score: {score}/100",
        "",
        "Summary",
        "-" * 20,
        summary or "No summary returned.",
        "",
        "Strengths",
        "-" * 20,
    ]

    lines.extend([f"- {item}" for item in strengths] or ["- No strengths returned."])

    lines.extend(["", "Weaknesses / Gaps", "-" * 20])
    lines.extend([f"- {item}" for item in weaknesses] or ["- No weaknesses returned."])

    lines.extend(["", "Recommendations", "-" * 20])
    lines.extend([f"- {item}" for item in recommendations] or ["- No recommendations returned."])

    lines.extend(["", "Job Description", "-" * 20, job_description])

    return "\n".join(lines)


def create_pdf_report(
    result: Dict[str, Any],
    cv_filename: str,
    job_description: str,
) -> Optional[bytes]:
    strengths = normalize_list(result.get("strengths") or result.get("matched_skills"))
    weaknesses = normalize_list(result.get("weaknesses") or result.get("missing_skills"))
    recommendations = normalize_list(result.get("recommendations"))

    data = {
        "cv_filename": cv_filename,
        "score": str(result.get("score", 0)),
        "summary": result.get("summary") or result.get("analysis") or "",
        "strengths_json": json.dumps(strengths, ensure_ascii=False),
        "weaknesses_json": json.dumps(weaknesses, ensure_ascii=False),
        "recommendations_json": json.dumps(recommendations, ensure_ascii=False),
        "job_description": job_description,
    }

    try:
        response = requests.post(
            api_url("/reports/analysis-pdf"),
            headers=get_auth_headers(),
            data=data,
            timeout=120,
        )

        if response.status_code == 403:
            st.warning("🔒 PDF Report is available in Pro.")
            st.page_link("pages/pricing.py", label="💳 Upgrade to Pro")
            return None

        if response.status_code == 401:
            st.error("You are not logged in or your session expired. Please log in again.")
            return None

        if response.status_code >= 400:
            st.error(f"PDF report failed. Backend returned {response.status_code}.")
            st.code(response.text)
            return None

        return response.content

    except requests.exceptions.Timeout:
        st.error("PDF report timed out. Please try again.")
        return None

    except Exception as exc:
        st.error(f"PDF report failed: {exc}")
        return None


def render_score(score: Any) -> None:
    try:
        numeric_score = int(float(score))
    except Exception:
        numeric_score = 0

    st.metric("Match Score", f"{numeric_score}/100")
    st.progress(max(0, min(numeric_score, 100)))


def render_analysis_result(
    result: Dict[str, Any],
    cv_filename: str,
    job_description: str,
) -> None:
    score = result.get("score", 0)
    summary = result.get("summary") or result.get("analysis") or ""
    strengths = normalize_list(result.get("strengths") or result.get("matched_skills"))
    weaknesses = normalize_list(result.get("weaknesses") or result.get("missing_skills"))
    recommendations = normalize_list(result.get("recommendations"))

    st.success("CV Analysis completed successfully.")
    render_score(score)

    if summary:
        st.markdown("### Summary")
        st.write(summary)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Strengths")
        if strengths:
            for item in strengths:
                st.write(f"✅ {item}")
        else:
            st.info("No strengths returned.")

    with col2:
        st.markdown("### Weaknesses / Gaps")
        if weaknesses:
            for item in weaknesses:
                st.write(f"⚠️ {item}")
        else:
            st.info("No weaknesses returned.")

    st.markdown("### Recommendations")
    if recommendations:
        for item in recommendations:
            st.write(f"💡 {item}")
    else:
        st.info("No recommendations returned.")

    report_text = build_text_report(
        result=result,
        cv_filename=cv_filename,
        job_description=job_description,
    )

    st.markdown("---")
    st.markdown("### Download Report")

    col_txt, col_pdf = st.columns(2)

    with col_txt:
        st.download_button(
            label="⬇️ Download Report TXT",
            data=report_text.encode("utf-8"),
            file_name="talentmatch_cv_analysis_report.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with col_pdf:
        if is_pro_user():
            pdf_bytes = create_pdf_report(
                result=result,
                cv_filename=cv_filename,
                job_description=job_description,
            )

            if pdf_bytes:
                st.download_button(
                    label="📄 Download PDF Report",
                    data=pdf_bytes,
                    file_name="talentmatch_cv_analysis_report.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
        else:
            st.info("🔒 PDF Report is available in Pro.")
            st.page_link("pages/pricing.py", label="💳 Upgrade to Pro")

    with st.expander("Raw response"):
        st.json(result)


def analyze_resume(uploaded_file, job_description: str) -> Optional[Dict[str, Any]]:
    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            uploaded_file.type or "application/pdf",
        )
    }

    data = {"job_description": job_description}

    try:
        response = requests.post(
            api_url("/analyze-resume"),
            headers=get_auth_headers(),
            files=files,
            data=data,
            timeout=120,
        )

        if response.status_code == 401:
            st.error("You are not logged in or your session expired. Please log in again.")
            return None

        if response.status_code == 403:
            st.error(
                "CV Analysis is currently blocked by backend permissions. "
                "Frontend is free, but backend returned 403."
            )
            return None

        if response.status_code == 429:
            st.error("Too many requests. Please wait a little and try again.")
            return None

        if response.status_code >= 400:
            try:
                detail = response.json()
            except Exception:
                detail = response.text

            st.error(f"CV Analysis failed. Backend returned {response.status_code}.")
            st.code(str(detail))
            return None

        return response.json()

    except requests.exceptions.Timeout:
        st.error("CV Analysis timed out. Please try again with a shorter CV or job description.")
        return None

    except Exception as exc:
        st.error(f"CV Analysis failed: {exc}")
        return None


st.markdown(
    """
    <div style="padding: 22px 0 16px 0;">
        <h1 style="font-size:52px; margin-bottom:8px;">📄 AI CV Analysis</h1>
        <p style="font-size:20px; color:#6b7280; max-width:900px;">
            Upload your CV and paste a job description to get an AI-powered match score,
            strengths, weaknesses, and practical recommendations.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

if not is_logged_in():
    st.warning("Please log in to use CV Analysis.")
    st.page_link("pages/login.py", label="🔐 Login")
    st.stop()

with st.container(border=True):
    uploaded_file = st.file_uploader(
        "Upload CV PDF",
        type=["pdf"],
        help="Upload a PDF CV/resume.",
    )

    job_description = st.text_area(
        "Paste job description",
        height=260,
        placeholder="Paste the full job description here...",
    )

    analyze_clicked = st.button(
        "🚀 Analyze CV",
        type="primary",
        use_container_width=True,
    )

if analyze_clicked:
    if uploaded_file is None:
        st.error("Please upload a PDF CV first.")
        st.stop()

    if not job_description.strip():
        st.error("Please paste a job description first.")
        st.stop()

    with st.spinner("Analyzing CV with AI..."):
        result = analyze_resume(uploaded_file, job_description.strip())

    if result:
        render_analysis_result(
            result=result,
            cv_filename=uploaded_file.name,
            job_description=job_description.strip(),
        )
