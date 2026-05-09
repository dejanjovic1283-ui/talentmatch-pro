from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests
import streamlit as st # pyright: ignore[reportMissingImports]


st.set_page_config(
    page_title="TalentMatch Pro",
    page_icon="🚀",
    layout="wide",
)

DEFAULT_BACKEND_URL = "https://talentmatch-backend-1283.onrender.com"
ANALYZE_ENDPOINT = "/analyze-test"  # Temporary production demo endpoint.
HISTORY_ENDPOINT = "/history"
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
    """Runtime configuration loaded from Streamlit secrets or environment variables."""

    backend_url: str
    firebase_api_key: str
    lemon_squeezy_checkout_url: str
    request_timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS


def get_secret_or_env(name: str, default: str = "") -> str:
    """Read a value from Streamlit secrets first, then from environment variables."""
    try:
        if name in st.secrets:
            value = st.secrets[name]
            if value is not None:
                return str(value).strip()
    except Exception:
        pass

    return os.getenv(name, default).strip()


def load_config() -> AppConfig:
    """Load application configuration."""
    backend_url = get_secret_or_env("BACKEND_URL", DEFAULT_BACKEND_URL)

    return AppConfig(
        backend_url=backend_url.rstrip("/"),
        firebase_api_key=get_secret_or_env("FIREBASE_API_KEY"),
        lemon_squeezy_checkout_url=get_secret_or_env("LEMON_SQUEEZY_CHECKOUT_URL"),
    )


def init_session_state() -> None:
    """Initialize Streamlit session state."""
    defaults: dict[str, Any] = {
        "user": None,
        "auth_error": "",
        "analysis_result": None,
        "last_uploaded_name": "",
        "job_description": DEFAULT_JOB_DESCRIPTION,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def firebase_auth_request(
    *,
    endpoint: str,
    email: str,
    password: str,
    config: AppConfig,
) -> dict[str, Any]:
    """Authenticate a user with Firebase Identity Toolkit REST API."""
    if not config.firebase_api_key:
        raise RuntimeError("FIREBASE_API_KEY is missing in Render environment variables.")

    url = (
        "https://identitytoolkit.googleapis.com/v1/"
        f"{endpoint}?key={config.firebase_api_key}"
    )

    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }

    response = requests.post(url, json=payload, timeout=30)
    data = response.json()

    if response.status_code >= 400:
        message = data.get("error", {}).get("message", "Authentication failed.")
        raise RuntimeError(message)

    return data


def save_user_session(data: dict[str, Any], email: str) -> None:
    """Save authenticated user data in session state."""
    st.session_state.user = {
        "email": email,
        "id_token": data.get("idToken", ""),
        "refresh_token": data.get("refreshToken", ""),
        "local_id": data.get("localId", ""),
    }


def sign_in(email: str, password: str, config: AppConfig) -> None:
    """Sign in an existing Firebase user."""
    data = firebase_auth_request(
        endpoint="accounts:signInWithPassword",
        email=email,
        password=password,
        config=config,
    )
    save_user_session(data, email)


def sign_up(email: str, password: str, config: AppConfig) -> None:
    """Create a new Firebase user."""
    data = firebase_auth_request(
        endpoint="accounts:signUp",
        email=email,
        password=password,
        config=config,
    )
    save_user_session(data, email)


def sign_out() -> None:
    """Clear the current session."""
    st.session_state.user = None
    st.session_state.auth_error = ""
    st.session_state.analysis_result = None
    st.rerun()


def get_id_token() -> str:
    """Return the current Firebase ID token."""
    user = st.session_state.get("user")
    if not isinstance(user, dict):
        return ""

    return str(user.get("id_token", "")).strip()


def get_auth_headers() -> dict[str, str]:
    """Build Authorization headers for protected backend endpoints."""
    token = get_id_token()
    if not token:
        return {}

    return {"Authorization": f"Bearer {token}"}


def require_auth() -> bool:
    """Require the user to be signed in before using the app."""
    if not get_id_token():
        st.warning("Please sign in before analyzing a CV.")
        return False

    return True


def extract_backend_error(response: requests.Response) -> str:
    """Return a readable backend error message."""
    try:
        payload = response.json()
    except ValueError:
        return response.text or f"Request failed with HTTP {response.status_code}."

    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str):
            return detail
        if isinstance(detail, list):
            return "; ".join(str(item) for item in detail)

    return str(payload)


def handle_backend_response(response: requests.Response) -> Any | None:
    """Handle common backend response cases."""
    if response.status_code == 401:
        st.error("Unauthorized. Please sign out and sign in again.")
        return None

    if response.status_code >= 400:
        st.error(extract_backend_error(response))
        return None

    try:
        return response.json()
    except ValueError:
        st.error("Backend returned a non-JSON response.")
        return None


def render_sidebar(config: AppConfig) -> None:
    """Render sidebar authentication and runtime info."""
    with st.sidebar:
        st.header("Authentication")

        user = st.session_state.get("user")

        if isinstance(user, dict) and user.get("email"):
            st.success(f"Signed in as\n\n{user['email']}")

            if st.button("Sign out", use_container_width=True):
                sign_out()

        else:
            auth_mode = st.radio(
                "Choose action",
                ["Sign in", "Create account"],
            )

            email = st.text_input("Email")
            password = st.text_input("Password", type="password")

            if st.button(auth_mode, use_container_width=True):
                try:
                    if not email.strip():
                        raise RuntimeError("Email is required.")
                    if not password:
                        raise RuntimeError("Password is required.")

                    if auth_mode == "Sign in":
                        sign_in(email.strip(), password, config)
                    else:
                        sign_up(email.strip(), password, config)

                    st.session_state.auth_error = ""
                    st.rerun()

                except Exception as exc:
                    st.session_state.auth_error = str(exc)

            if st.session_state.auth_error:
                st.error(st.session_state.auth_error)

        st.divider()
        st.caption(f"Backend URL: {config.backend_url}")
        st.caption(f"Endpoint: {ANALYZE_ENDPOINT}")


def render_header() -> None:
    """Render the main app header."""
    st.title("🚀 TalentMatch Pro")
    st.caption(
        "Upload your PDF CV, paste a job description, and get an AI-powered match score."
    )


def validate_inputs(uploaded_file: Any | None, job_description: str) -> list[str]:
    """Validate the uploaded file and job description."""
    errors: list[str] = []

    if uploaded_file is None:
        errors.append("Please upload a PDF CV.")
    else:
        file_name = str(getattr(uploaded_file, "name", ""))
        if not file_name.lower().endswith(".pdf"):
            errors.append("Only PDF files are supported.")

    if not job_description.strip():
        errors.append("Please paste a job description.")
    elif len(job_description.strip()) < 40:
        errors.append("The job description is too short.")

    return errors


def get_score_verdict(score: int | float) -> tuple[str, str]:
    """Return a human-readable verdict and visual level from a score."""
    if score >= 80:
        return "🔥 Strong Match", "success"

    if score >= 60:
        return "✅ Good Match", "warning"

    return "⚠️ Weak Match", "error"


def render_analyze_page(config: AppConfig) -> None:
    """Render the CV analysis page."""
    st.subheader("Analyze CV")

    if not require_auth():
        return

    uploaded_file = st.file_uploader(
        "Upload your CV as a PDF",
        type=["pdf"],
        accept_multiple_files=False,
        help="PDF only.",
    )

    if uploaded_file is not None:
        file_size_kb = len(uploaded_file.getvalue()) / 1024
        st.info(f"Selected file: {uploaded_file.name} ({file_size_kb:.1f} KB)")

    job_description = st.text_area(
        "Paste the job description",
        key="job_description",
        height=260,
        placeholder="Paste the job description here...",
    )

    if st.button("Analyze CV", use_container_width=True):
        errors = validate_inputs(uploaded_file, job_description)
        if errors:
            for error in errors:
                st.error(error)
            return

        files = {
            "file": (
                uploaded_file.name if uploaded_file else "resume.pdf",
                uploaded_file.getvalue() if uploaded_file else b"",
                "application/pdf",
            )
        }

        data = {
            "job_description": job_description,
        }

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

        st.session_state.analysis_result = result
        st.session_state.last_uploaded_name = (
    uploaded_file.name if uploaded_file else "resume.pdf"
)
        st.success("Analysis completed successfully.")

    render_analysis_result()


def render_analysis_result() -> None:
    """Render the latest analysis result with a cleaner SaaS-style UI."""
    result = st.session_state.get("analysis_result")

    if not isinstance(result, dict):
        return

    st.divider()
    st.header("Analysis result")

    raw_score = result.get("score", 0)

    try:
        score = int(raw_score)
    except (TypeError, ValueError):
        score = 0

    verdict, level = get_score_verdict(score)

    if level == "success":
        st.success(f"{verdict} — {score}/100")
    elif level == "warning":
        st.warning(f"{verdict} — {score}/100")
    else:
        st.error(f"{verdict} — {score}/100")

    col_score, col_verdict, col_file = st.columns([1, 1, 2])

    col_score.metric("Match Score", f"{score}/100")
    col_verdict.metric("Verdict", verdict.replace("🔥 ", "").replace("✅ ", "").replace("⚠️ ", ""))

    uploaded_name = st.session_state.get("last_uploaded_name")
    if uploaded_name:
        col_file.write(f"**CV file:** {uploaded_name}")

    summary = result.get("summary", "")
    if summary:
        st.subheader("📝 Summary")
        st.write(summary)

    strengths = result.get("strengths") or result.get("matched_skills") or []
    weaknesses = result.get("weaknesses") or result.get("missing_skills") or []
    recommendations = result.get("recommendations") or []

    col_left, col_right = st.columns(2)

    with col_left:
        render_list("✅ Strengths", strengths, empty_text="No strengths detected.")

    with col_right:
        render_list("❌ Missing Skills", weaknesses, empty_text="No missing skills detected.")

    render_list(
        "💡 Recommendations",
        recommendations,
        empty_text="No recommendations available.",
    )

    st.info(
        "Upgrade to TalentMatch Pro for advanced recruiter insights, ATS optimization, and AI interview preparation."
    )

    with st.expander("Raw JSON response"):
        st.json(result)


def render_list(title: str, items: Any, empty_text: str) -> None:
    """Render a titled list section."""
    st.subheader(title)

    if isinstance(items, list) and items:
        for item in items:
            st.markdown(f"- {item}")
        return

    if isinstance(items, str) and items.strip():
        st.write(items)
        return

    st.caption(empty_text)


def render_history_page(config: AppConfig) -> None:
    """Render the history page placeholder."""
    st.subheader("History")
    st.info(
        "History will be enabled after the production auth and database flow is fully restored."
    )


def render_upgrade_page(config: AppConfig) -> None:
    """Render the upgrade page."""
    st.subheader("Upgrade")

    st.write(
        "Free users can test TalentMatch Pro. Pro users will get unlimited analyses, saved history, and advanced insights."
    )

    if config.lemon_squeezy_checkout_url:
        st.link_button(
            "Upgrade with Lemon Squeezy",
            config.lemon_squeezy_checkout_url,
            use_container_width=True,
        )
    else:
        st.warning("Lemon Squeezy checkout is not configured yet.")


def render_backend_status(config: AppConfig) -> None:
    """Render backend status information."""
    st.subheader("Backend")

    st.write(f"Backend URL: `{config.backend_url}`")
    st.write(f"Analyze endpoint: `{ANALYZE_ENDPOINT}`")

    if st.button("Check backend", use_container_width=True):
        try:
            response = requests.get(f"{config.backend_url}/", timeout=20)
        except requests.RequestException as exc:
            st.error(f"Backend is unreachable: {exc}")
            return

        if response.status_code >= 400:
            st.error(f"Backend returned HTTP {response.status_code}.")
            st.text(response.text)
            return

        st.success("Backend is reachable.")

        try:
            st.json(response.json())
        except ValueError:
            st.write(response.text)


def main() -> None:
    """Run the Streamlit application."""
    config = load_config()
    init_session_state()
    render_sidebar(config)
    render_header()

    tab_analyze, tab_history, tab_upgrade, tab_backend = st.tabs(
        ["Analyze CV", "History", "Upgrade", "Backend"]
    )

    with tab_analyze:
        render_analyze_page(config)

    with tab_history:
        render_history_page(config)

    with tab_upgrade:
        render_upgrade_page(config)

    with tab_backend:
        render_backend_status(config)


if __name__ == "__main__":
    main()