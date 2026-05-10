from __future__ import annotations

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
ANALYZE_ENDPOINT = "/analyze-test"
HISTORY_ENDPOINT = "/history-test"
ME_ENDPOINT = "/me"
CHECKOUT_ENDPOINT = "/billing/create-checkout"
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
    firebase_api_key: str
    request_timeout_seconds: int


def get_secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, default)
    except Exception:
        value = os.getenv(name, default)

    return str(value).strip()


def load_config() -> AppConfig:
    backend_url = get_secret("BACKEND_URL", DEFAULT_BACKEND_URL).rstrip("/")
    firebase_api_key = get_secret("FIREBASE_API_KEY", "")

    timeout_raw = get_secret(
        "REQUEST_TIMEOUT_SECONDS",
        str(DEFAULT_REQUEST_TIMEOUT_SECONDS),
    )

    try:
        timeout = int(timeout_raw)
    except ValueError:
        timeout = DEFAULT_REQUEST_TIMEOUT_SECONDS

    return AppConfig(
        backend_url=backend_url,
        firebase_api_key=firebase_api_key,
        request_timeout_seconds=timeout,
    )


def get_auth_headers() -> dict[str, str]:
    user = st.session_state.get("user")

    if isinstance(user, dict):
        token = user.get("id_token", "")
    else:
        token = ""

    if not token:
        return {}

    return {"Authorization": f"Bearer {token}"}


def firebase_auth_url(config: AppConfig, action: str) -> str:
    endpoint = "signUp" if action == "signup" else "signInWithPassword"

    return (
        f"https://identitytoolkit.googleapis.com/v1/accounts:{endpoint}"
        f"?key={config.firebase_api_key}"
    )


def authenticate_user(
    config: AppConfig,
    email: str,
    password: str,
    action: str,
) -> tuple[bool, str]:
    if not config.firebase_api_key:
        return False, "FIREBASE_API_KEY is missing in Streamlit secrets."

    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }

    try:
        response = requests.post(
            firebase_auth_url(config, action),
            json=payload,
            timeout=30,
        )
    except requests.RequestException as exc:
        return False, f"Auth request failed: {exc}"

    if response.status_code != 200:
        try:
            detail = response.json()
            message = detail.get("error", {}).get("message", response.text)
        except Exception:
            message = response.text

        return False, message

    data = response.json()

    st.session_state["user"] = {
        "email": data.get("email", email),
        "id_token": data.get("idToken", ""),
        "refresh_token": data.get("refreshToken", ""),
        "local_id": data.get("localId", ""),
    }

    return True, "Signed in successfully."


def sign_out() -> None:
    for key in ["user", "analysis_result", "last_uploaded_name", "last_job_description"]:
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
        action_label = st.sidebar.radio(
            "Choose action",
            ["Sign in", "Create account"],
            horizontal=False,
        )

        email = st.sidebar.text_input("Email")
        password = st.sidebar.text_input("Password", type="password")

        action = "signup" if action_label == "Create account" else "signin"

        if st.sidebar.button(action_label, use_container_width=True):
            ok, message = authenticate_user(config, email, password, action)

            if ok:
                st.sidebar.success(message)
                st.rerun()
            else:
                st.sidebar.error(message)

    st.sidebar.divider()
    st.sidebar.caption(f"Backend URL: {config.backend_url}")
    st.sidebar.caption(f"Endpoint: {ANALYZE_ENDPOINT}")


def render_hero() -> None:
    st.markdown(
        """
        <div style="padding: 28px 0 12px 0;">
            <h1 style="font-size: 52px; margin-bottom: 8px;">
                🚀 TalentMatch Pro
            </h1>
            <p style="font-size: 18px; color: #6b7280; margin-top: 0;">
                AI-powered CV matching, ATS keyword analysis, and job application insights.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info("📄 Upload a CV and compare it against a real job description.")

    with col2:
        st.info("🎯 Use ATS Checker to find missing keywords.")

    with col3:
        st.info("📥 Download a shareable analysis report.")


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
        st.error(response.text)
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

    strengths = result.get("strengths", [])
    weaknesses = result.get("weaknesses", [])
    recommendations = result.get("recommendations", [])

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

    for item in strengths:
        lines.append(f"- {item}")

    lines.extend(["", "Missing Skills", "-" * 20])

    for item in weaknesses:
        lines.append(f"- {item}")

    lines.extend(["", "Recommendations", "-" * 20])

    for item in recommendations:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "Job Description",
            "-" * 20,
            job_description,
            "",
            "Generated by TalentMatch Pro",
        ]
    )

    return "\n".join(lines)


def render_download_report(result: dict[str, Any]) -> None:
    report_text = build_text_report(result)
    cv_file = st.session_state.get("last_uploaded_name", "resume")
    safe_name = str(cv_file).replace(".pdf", "").replace(" ", "_")

    st.download_button(
        label="📥 Download Report",
        data=report_text,
        file_name=f"{safe_name}_talentmatch_report.txt",
        mime="text/plain",
        use_container_width=True,
    )


def render_analysis_result() -> None:
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

    render_download_report(result)

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

    st.info(
        "Next step: open the ATS Checker page to see exact missing keywords "
        "from the job description."
    )


def render_analyze_page(config: AppConfig) -> None:
    st.subheader("Analyze CV")

    user = st.session_state.get("user")

    if not isinstance(user, dict) or not user.get("id_token"):
        st.warning("Please sign in before analyzing a CV.")
        return

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
            return

        if not job_description.strip():
            st.error("Please paste a job description.")
            return

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
                    headers=get_auth_headers(),
                    data=data,
                    files=files,
                    timeout=config.request_timeout_seconds,
                )
            except requests.RequestException as exc:
                st.error(f"Backend request failed: {exc}")
                return

        result = handle_backend_response(response)

        if result is None:
            return

        st.session_state["analysis_result"] = result
        st.session_state["last_uploaded_name"] = uploaded_file.name
        st.session_state["last_job_description"] = job_description
        st.success("Analysis completed successfully.")

    render_analysis_result()


def render_history_preview() -> None:
    st.subheader("History")
    st.info("Open the History page from the sidebar to review previous analysis results.")


def render_upgrade_preview() -> None:
    st.subheader("Upgrade")
    st.info(
        "Pro features will include advanced recruiter insights, ATS optimization, "
        "PDF export reports, and CV rewrite suggestions."
    )


def render_backend_status(config: AppConfig) -> None:
    st.subheader("Backend Status")

    try:
        response = requests.get(f"{config.backend_url}/healthz", timeout=20)
    except requests.RequestException as exc:
        st.error(f"Backend unavailable: {exc}")
        return

    if response.status_code == 200:
        st.success("Backend is live.")
        st.json(response.json())
    else:
        st.error(response.text)


def main() -> None:
    config = load_config()

    render_sidebar(config)
    render_hero()

    tabs = st.tabs(["Analyze CV", "History", "Upgrade", "Backend"])

    with tabs[0]:
        render_analyze_page(config)

    with tabs[1]:
        render_history_preview()

    with tabs[2]:
        render_upgrade_preview()

    with tabs[3]:
        render_backend_status(config)


if __name__ == "__main__":
    main()