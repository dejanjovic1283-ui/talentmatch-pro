from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests
import streamlit as st

st.set_page_config(
    page_title="TalentMatch Pro",
    page_icon="🚀",
    layout="wide",
)

DEFAULT_BACKEND_URL = "https://talentmatch-backend-1283.onrender.com"
ANALYZE_ENDPOINT = "/analyze-resume"
PDF_REPORT_ENDPOINT = "/reports/analysis-pdf"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 120

DEFAULT_JOB_DESCRIPTION = """
Founding Full-Stack AI SaaS Engineer

We are building TalentMatch Pro, an AI-powered SaaS platform that helps job seekers compare their CVs against real job descriptions, identify gaps, and improve their application strategy.

What you will do:
- Build and scale a FastAPI + Streamlit product
- Integrate Firebase authentication and storage
- Ship AI-powered CV analysis with OpenAI
- Own billing workflows with Lemon Squeezy
- Improve product reliability, UX, and deployment pipelines

What we are looking for:
- Strong Python backend fundamentals
- Experience with APIs, auth, databases, and SaaS integrations
- Product mindset and ability to ship independently
- Familiarity with cloud deployment and developer tooling

Nice to have:
- Experience with AI products, prompt design, and PDF/document processing
- Experience building MVPs from zero to first users
""".strip()


@dataclass(frozen=True)
class AppConfig:
    backend_url: str
    request_timeout_seconds: int


def load_config() -> AppConfig:
    backend_url = os.getenv("BACKEND_URL", DEFAULT_BACKEND_URL).rstrip("/")

    try:
        timeout = int(os.getenv("REQUEST_TIMEOUT_SECONDS", str(DEFAULT_REQUEST_TIMEOUT_SECONDS)))
    except ValueError:
        timeout = DEFAULT_REQUEST_TIMEOUT_SECONDS

    return AppConfig(
        backend_url=backend_url,
        request_timeout_seconds=timeout,
    )


def get_auth_headers() -> dict[str, str]:
    user = st.session_state.get("user")

    if not isinstance(user, dict):
        return {}

    token = user.get("id_token") or user.get("idToken") or ""

    if not token:
        return {}

    return {"Authorization": f"Bearer {token}"}


def sign_out() -> None:
    for key in [
        "user",
        "analysis_result",
        "last_uploaded_name",
        "last_job_description",
        "pdf_report_bytes",
    ]:
        st.session_state.pop(key, None)


def render_sidebar(config: AppConfig) -> None:
    st.sidebar.markdown("## Authentication")

    user = st.session_state.get("user")

    if isinstance(user, dict) and user.get("id_token"):
        st.sidebar.success("Signed in as")
        st.sidebar.markdown(user.get("email", "Unknown user"))

        if st.sidebar.button("Sign out", use_container_width=True):
            sign_out()
            st.rerun()
    else:
        st.sidebar.warning("Please login first.")
        st.sidebar.page_link("pages/login.py", label="Login", icon="🔐")
        st.sidebar.page_link("pages/register.py", label="Register", icon="🚀")

    st.sidebar.divider()
    st.sidebar.caption(f"Backend URL: {config.backend_url}")
    st.sidebar.caption(f"Endpoint: {ANALYZE_ENDPOINT}")


def score_verdict(score: int) -> tuple[str, str]:
    if score >= 80:
        return "Strong Match", "🔥"
    if score >= 60:
        return "Good Match", "✅"
    return "Weak Match", "⚠️"


def handle_backend_response(response: requests.Response) -> dict[str, Any] | None:
    if response.status_code == 401:
        st.error("Unauthorized. Please sign out and sign in again.")
        return None

    if response.status_code == 403:
        st.error(response.text)
        return None

    if response.status_code == 429:
        st.error("Too Many Requests")
        return None

    if response.status_code != 200:
        st.error(response.text[:1000])
        return None

    try:
        return response.json()
    except ValueError:
        st.error("Backend returned invalid JSON.")
        return None


def build_text_report(result: dict[str, Any]) -> str:
    score = int(result.get("score", 0) or 0)
    verdict, icon = score_verdict(score)

    cv_file = st.session_state.get("last_uploaded_name", "resume.pdf")
    job_description = st.session_state.get("last_job_description", "")

    lines = [
        "TalentMatch Pro - CV Analysis Report",
        "=" * 42,
        f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"CV file: {cv_file}",
        f"Match score: {score}/100",
        f"Verdict: {icon} {verdict}",
        "",
        "Summary",
        "-" * 20,
        result.get("summary", ""),
        "",
        "Strengths",
        "-" * 20,
    ]

    for item in result.get("strengths", []):
        lines.append(f"- {item}")

    lines.extend(["", "Missing Skills", "-" * 20])

    for item in result.get("weaknesses", []):
        lines.append(f"- {item}")

    lines.extend(["", "Recommendations", "-" * 20])

    for item in result.get("recommendations", []):
        lines.append(f"- {item}")

    lines.extend(["", "Job Description", "-" * 20, job_description])

    return "\n".join(lines)


def fetch_pdf_report(config: AppConfig, result: dict[str, Any]) -> bytes | None:
    headers = get_auth_headers()

    if not headers:
        st.error("Missing auth token. Please login again.")
        return None

    cv_filename = str(st.session_state.get("last_uploaded_name", "resume.pdf"))
    job_description = str(st.session_state.get("last_job_description", ""))

    data = {
        "cv_filename": cv_filename,
        "score": str(int(result.get("score", 0) or 0)),
        "summary": str(result.get("summary", "")),
        "strengths_json": json.dumps(result.get("strengths", [])),
        "weaknesses_json": json.dumps(result.get("weaknesses", [])),
        "recommendations_json": json.dumps(result.get("recommendations", [])),
        "job_description": job_description,
    }

    try:
        response = requests.post(
            f"{config.backend_url}{PDF_REPORT_ENDPOINT}",
            headers=headers,
            data=data,
            timeout=config.request_timeout_seconds,
        )
    except requests.RequestException as exc:
        st.error(f"PDF report request failed: {exc}")
        return None

    if response.status_code != 200:
        st.error(response.text[:1000])
        return None

    return response.content


def render_analysis_result(config: AppConfig) -> None:
    result = st.session_state.get("analysis_result")

    if not isinstance(result, dict):
        return

    score = int(result.get("score", 0) or 0)
    verdict, icon = score_verdict(score)

    st.divider()
    st.header("Analysis result")

    if score >= 80:
        st.success(f"{icon} {verdict} — {score}/100")
    elif score >= 60:
        st.warning(f"{icon} {verdict} — {score}/100")
    else:
        st.error(f"{icon} {verdict} — {score}/100")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Match Score", f"{score}/100")

    with col2:
        st.metric("Verdict", verdict)

    with col3:
        st.metric("CV file", st.session_state.get("last_uploaded_name", "resume.pdf"))

    st.progress(min(max(score, 0), 100) / 100)

    cv_file = str(st.session_state.get("last_uploaded_name", "resume")).replace(".pdf", "")

    txt_col, pdf_col = st.columns(2)

    with txt_col:
        report_text = build_text_report(result)

        st.download_button(
            "📥 Download TXT Report",
            data=report_text,
            file_name=f"{cv_file}_talentmatch_report.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with pdf_col:
        if st.button("📄 Generate PDF Report", use_container_width=True):
            with st.spinner("Generating PDF report..."):
                pdf_bytes = fetch_pdf_report(config, result)

            if pdf_bytes:
                st.session_state["pdf_report_bytes"] = pdf_bytes
                st.success("PDF report generated.")

        pdf_bytes = st.session_state.get("pdf_report_bytes")

        if isinstance(pdf_bytes, bytes):
            st.download_button(
                "⬇️ Download PDF Report",
                data=pdf_bytes,
                file_name=f"{cv_file}_talentmatch_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

    st.markdown("## 📝 Summary")
    st.write(result.get("summary", ""))

    left, right = st.columns(2)

    with left:
        st.markdown("## ✅ Strengths")
        for item in result.get("strengths", []):
            st.markdown(f"- {item}")

    with right:
        st.markdown("## ❌ Missing Skills")
        for item in result.get("weaknesses", []):
            st.markdown(f"- {item}")

    st.markdown("## 💡 Recommendations")
    for item in result.get("recommendations", []):
        st.markdown(f"- {item}")


def main() -> None:
    config = load_config()

    render_sidebar(config)

    st.title("🚀 TalentMatch Pro")
    st.caption("AI-powered CV matching, ATS keyword analysis, and job application insights.")

    user = st.session_state.get("user")

    if not isinstance(user, dict) or not user.get("id_token"):
        st.warning("Please login before analyzing a CV.")
        st.stop()

    uploaded_file = st.file_uploader(
        "Upload your CV as a PDF",
        type=["pdf"],
        accept_multiple_files=False,
    )

    job_description = st.text_area(
        "Paste the job description",
        value=DEFAULT_JOB_DESCRIPTION,
        height=320,
    )

    if uploaded_file is not None:
        file_size_kb = len(uploaded_file.getvalue()) / 1024
        st.info(f"Selected file: {uploaded_file.name} ({file_size_kb:.1f} KB)")

    if st.button("Analyze CV", use_container_width=True):
        if uploaded_file is None:
            st.error("Please upload a PDF CV.")
            st.stop()

        if not job_description.strip():
            st.error("Please paste a job description.")
            st.stop()

        headers = get_auth_headers()

        if not headers:
            st.error("Missing auth token. Please login again.")
            st.stop()

        files = {
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                "application/pdf",
            )
        }

        data = {"job_description": job_description}

        with st.spinner("Analyzing CV..."):
            try:
                response = requests.post(
                    f"{config.backend_url}{ANALYZE_ENDPOINT}",
                    headers=headers,
                    data=data,
                    files=files,
                    timeout=config.request_timeout_seconds,
                )
            except requests.RequestException as exc:
                st.error(f"Backend request failed: {exc}")
                st.stop()

        result = handle_backend_response(response)

        if result is None:
            st.stop()

        st.session_state["analysis_result"] = result
        st.session_state["last_uploaded_name"] = uploaded_file.name
        st.session_state["last_job_description"] = job_description
        st.session_state.pop("pdf_report_bytes", None)

        st.success("Analysis completed successfully.")

    render_analysis_result(config)


if __name__ == "__main__":
    main()