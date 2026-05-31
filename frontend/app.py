import json
import os
import time
from pathlib import Path
from typing import Any

import streamlit as st

from auth_utils import (
    api_post,
    clear_auth,
    get_profile,
    is_logged_in,
    is_pro_user,
    refresh_profile,
)


BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "logo.png"
FAVICON_PATH = ASSETS_DIR / "favicon.png"


def is_valid_image(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False

    try:
        from PIL import Image

        with Image.open(path) as image:
            image.verify()
        return True
    except Exception:
        return False


ADMIN_EMAILS = {
    "dejan.jovic1283@gmail.com",
    "dejanjovicjovic5@gmail.com",
}

extra_admins = os.getenv("ADMIN_EMAILS", "").strip()
if extra_admins:
    ADMIN_EMAILS.update(
        email.strip().lower()
        for email in extra_admins.split(",")
        if email.strip()
    )


st.set_page_config(
    page_title="TalentMatch Pro",
    page_icon=str(FAVICON_PATH) if is_valid_image(FAVICON_PATH) else "🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)


def maybe_refresh_profile(force: bool = False) -> dict[str, Any]:
    if not is_logged_in():
        return {}

    now = time.time()
    last_refresh = float(st.session_state.get("profile_last_refresh", 0) or 0)

    if force or now - last_refresh > 60 or not st.session_state.get("profile"):
        profile = refresh_profile() or {}
        st.session_state["profile_last_refresh"] = now
        return profile

    return get_profile() or {}


def current_user_email() -> str:
    user = st.session_state.get("user")

    if isinstance(user, dict):
        return str(user.get("email") or "").strip().lower()

    profile = get_profile() or {}
    return str(profile.get("email") or "").strip().lower()


def is_admin_user() -> bool:
    return current_user_email() in ADMIN_EMAILS


def extract_error_message(response) -> str:
    status_code = getattr(response, "status_code", None)
    text = getattr(response, "text", "") or ""

    try:
        payload = response.json()
    except Exception:
        if status_code:
            return f"{status_code}: {text[:1000]}"
        return text[:1000] or "Unknown backend error."

    if not isinstance(payload, dict):
        return str(payload)

    detail = payload.get("detail")
    error = payload.get("error")

    if isinstance(detail, dict):
        message = detail.get("message") or str(detail)
    elif detail:
        message = str(detail)
    elif error:
        message = str(error)
    else:
        message = str(payload)

    if status_code:
        return f"{status_code}: {message}"

    return message


def analyze_cv(uploaded_file, job_description: str):
    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            "application/pdf",
        )
    }

    data = {
        "job_description": job_description.strip(),
    }

    response = api_post(
        "/analyze-resume",
        data=data,
        files=files,
        timeout=180,
    )

    if response.status_code != 200:
        st.error(f"Analysis failed: {extract_error_message(response)}")

        if response.status_code == 403:
            st.warning("Free plan limit reached or Pro access required.")
            st.page_link("pages/pricing.py", label="🚀 Upgrade to Pro")

        if response.status_code == 429:
            st.warning("OpenAI rate limit or quota exceeded. Please try again later.")

        return None

    try:
        payload = response.json()
    except Exception:
        st.error(f"Backend returned invalid JSON: {response.text[:1000]}")
        return None

    if not isinstance(payload, dict):
        st.error("Backend returned invalid response format.")
        st.json(payload)
        return None

    return payload


def generate_pdf_report(result: dict, job_description: str):
    data = {
        "cv_filename": result.get("cv_filename", "resume.pdf"),
        "score": str(int(result.get("score") or result.get("match_score") or 0)),
        "summary": result.get("summary", ""),
        "strengths_json": json.dumps(result.get("strengths", [])),
        "weaknesses_json": json.dumps(result.get("weaknesses") or result.get("missing_skills") or []),
        "recommendations_json": json.dumps(result.get("recommendations", [])),
        "job_description": job_description or "",
    }

    response = api_post(
        "/reports/analysis-pdf",
        data=data,
        timeout=120,
    )

    if response.status_code != 200:
        st.error(f"PDF report failed: {extract_error_message(response)}")

        if response.status_code == 403:
            st.warning("PDF reports are a Pro feature.")
            st.page_link("pages/pricing.py", label="🚀 Upgrade to Pro")

        return None

    return getattr(response, "content", None)


def render_global_sidebar(profile: dict[str, Any], is_pro: bool) -> None:
    with st.sidebar:
        if is_valid_image(LOGO_PATH):
            st.image(str(LOGO_PATH), use_container_width=True)
        else:
            st.markdown("# 🎯 TalentMatch Pro")

        st.caption("AI-powered CV analysis and ATS optimization")
        st.divider()

        st.markdown("### Authentication")

        if is_logged_in() and isinstance(st.session_state.get("user"), dict):
            email = st.session_state["user"].get("email", "")
            st.success(f"Signed in as\n\n{email}")

            plan = "PRO" if is_pro else "FREE"
            st.caption(f"Current plan: {plan}")

            if st.button("Refresh profile", use_container_width=True):
                maybe_refresh_profile(force=True)
                st.rerun()

            if st.button("Logout", use_container_width=True):
                clear_auth()
                st.rerun()
        else:
            st.warning("Not signed in")
            if st.button("Login", use_container_width=True):
                st.switch_page("pages/login.py")


def dashboard_page() -> None:
    profile = maybe_refresh_profile()
    is_pro = is_pro_user()

    st.markdown("# 🚀 TalentMatch Pro")
    st.markdown("### AI-powered CV analysis for modern job seekers")
    st.write("Optimize your CV, identify missing skills, improve ATS performance, and increase interview chances.")

    st.caption("Plan: ⭐ PRO" if is_pro else "Plan: FREE")
    st.caption("AI-powered CV matching, ATS keyword analysis, and job application insights.")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("AI CV Match", "GPT Powered")

    with col2:
        st.metric("ATS Scanner", "Built In")

    with col3:
        st.metric("Semantic Match", "Enabled" if is_pro else "Upgrade")

    with col4:
        st.metric("Recruiter Mode", "Enabled" if is_pro else "Upgrade")

    st.divider()

    if not is_logged_in():
        st.warning("Please login before analyzing a CV.")
    elif not is_pro:
        used = int(profile.get("analyses_used", 0) or 0)
        limit = int(profile.get("free_limit", 3) or 3)
        remaining = max(limit - used, 0)

        st.info(f"Free plan: {used}/{limit} analyses used. Remaining: {remaining}")

        if limit:
            st.progress(min(used / limit, 1))

        if remaining == 0:
            st.warning("Free limit reached. Upgrade to Pro to continue.")
            st.page_link("pages/pricing.py", label="🚀 Upgrade to Pro")

    uploaded_file = st.file_uploader("Upload your CV as a PDF", type=["pdf"])

    if uploaded_file:
        st.session_state["last_uploaded_name"] = uploaded_file.name
        st.success(f"Selected file: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")

    job_description = st.text_area(
        "Paste the job description",
        value=st.session_state.get("last_job_description", ""),
        placeholder=(
            "Paste the job description here...\n\n"
            "Example:\n"
            "Senior Backend Engineer\n\n"
            "Requirements:\n"
            "• Python\n"
            "• FastAPI\n"
            "• PostgreSQL\n"
            "• Docker\n"
            "Responsibilities:\n"
            "• Build APIs\n"
            "• Improve reliability\n"
            "• Deploy cloud services"
        ),
        height=220,
    )

    st.session_state["last_job_description"] = job_description

    job_description_filled = bool(job_description and job_description.strip())

    if st.button(
        "Analyze CV",
        use_container_width=True,
        disabled=not (is_logged_in() and uploaded_file and job_description_filled),
    ):
        with st.spinner("Analyzing CV with AI..."):
            result = analyze_cv(uploaded_file, job_description or "")

        if result:
            result["cv_filename"] = (
                uploaded_file.name
                if uploaded_file
                else st.session_state.get("last_uploaded_name", "resume.pdf")
            )

            st.session_state["analysis_result"] = result
            maybe_refresh_profile(force=True)
            st.success("Analysis completed successfully.")
            st.rerun()

    if not is_logged_in():
        st.info("Login first to run an analysis.")
    elif not uploaded_file:
        st.info("Upload a PDF CV to start.")
    elif not job_description_filled:
        st.info("Paste a job description to continue.")

    result = st.session_state.get("analysis_result")

    if result:
        st.divider()
        st.markdown("## Analysis result")

        score = int(result.get("score") or result.get("match_score") or 0)
        verdict = result.get("verdict") or (
            "Strong Match" if score >= 80 else "Good Match" if score >= 60 else "Weak Match"
        )

        if score >= 80:
            st.success(f"🔥 {verdict} — {score}/100")
        elif score >= 60:
            st.warning(f"⚡ {verdict} — {score}/100")
        else:
            st.error(f"⚠️ {verdict} — {score}/100")

        metrics = st.columns(3)
        metrics[0].metric("Match Score", f"{score}/100")
        metrics[1].metric("Verdict", verdict)
        metrics[2].metric(
            "CV file",
            result.get("cv_filename", st.session_state.get("last_uploaded_name", "resume.pdf")),
        )

        st.progress(min(score / 100, 1.0))

        strengths = result.get("strengths", [])
        weaknesses = result.get("weaknesses") or result.get("missing_skills") or []
        recommendations = result.get("recommendations", [])

        txt_lines = [
            "TalentMatch Pro CV Analysis Report",
            "=" * 40,
            "",
            f"Score: {score}/100",
            f"Verdict: {verdict}",
            "",
            "Summary",
            "-" * 20,
            result.get("summary", ""),
            "",
            "Strengths",
            "-" * 20,
        ]

        txt_lines += [f"- {s}" for s in strengths] or ["No strengths returned."]
        txt_lines += ["", "Missing Skills", "-" * 20]
        txt_lines += [f"- {w}" for w in weaknesses] or ["No missing skills returned."]
        txt_lines += ["", "Recommendations", "-" * 20]
        txt_lines += [f"- {r}" for r in recommendations] or ["No recommendations returned."]
        txt_lines += ["", "Job Description", "-" * 20, job_description]

        txt_report = "\n".join(txt_lines)

        download_col1, download_col2 = st.columns(2)

        with download_col1:
            st.download_button(
                "📥 Download TXT Report",
                data=txt_report,
                file_name="talentmatch_report.txt",
                mime="text/plain",
                use_container_width=True,
            )

        with download_col2:
            if is_pro:
                pdf_bytes = generate_pdf_report(result, job_description or "")

                if pdf_bytes:
                    st.download_button(
                        "📄 Download PDF Report",
                        data=pdf_bytes,
                        file_name="talentmatch_report.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )
            else:
                st.button("📄 Download PDF Report (Pro)", use_container_width=True, disabled=True)
                st.caption("Upgrade to Pro to export PDF reports.")

        st.divider()

        st.markdown("## 📝 Summary")
        st.write(result.get("summary", "No summary available."))

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("## ✅ Strengths")
            if strengths:
                for item in strengths:
                    st.markdown(f"- {item}")
            else:
                st.write("No strengths returned.")

        with col2:
            st.markdown("## ❌ Missing Skills")
            if weaknesses:
                for item in weaknesses:
                    st.markdown(f"- {item}")
            else:
                st.write("No missing skills returned.")

        st.markdown("## 💡 Recommendations")

        if recommendations:
            for item in recommendations:
                st.markdown(f"- {item}")
        else:
            st.write("No recommendations returned.")


def account_page() -> None:
    profile = maybe_refresh_profile(force=True) if is_logged_in() else {}
    is_pro = is_pro_user()
    email = current_user_email()

    st.markdown("# ⚙️ Account")
    st.write("Manage your TalentMatch Pro account, subscription, and session.")

    st.divider()

    if not is_logged_in():
        st.warning("You are not signed in.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔐 Login", use_container_width=True):
                st.switch_page("pages/login.py")
        with col2:
            if st.button("📝 Register", use_container_width=True):
                st.switch_page("pages/register.py")
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Plan", "PRO" if is_pro else "FREE")

    with col2:
        used = int(profile.get("analyses_used", 0) or 0)
        limit = profile.get("free_limit", "∞" if is_pro else 3)
        st.metric("Analyses", f"{used}/{limit}")

    with col3:
        st.metric("Admin", "Yes" if is_admin_user() else "No")

    st.subheader("Profile")
    st.write(f"**Email:** {email or 'Unknown'}")
    st.write(f"**User ID:** {profile.get('id', 'Unknown')}")

    st.subheader("Subscription")

    if is_pro:
        st.success("You are currently on the Pro plan.")

        if st.button("💳 Manage Billing", use_container_width=True):
            response = api_post("/billing/create-portal", timeout=60)

            if response.status_code == 200:
                try:
                    data = response.json()
                except Exception:
                    st.error("Billing portal returned invalid response.")
                    return

                portal_url = data.get("url") or data.get("portal_url")
                if portal_url:
                    st.link_button("Open Billing Portal", portal_url, use_container_width=True)
                else:
                    st.error("Billing portal URL missing.")
            else:
                st.error(f"Billing portal failed: {extract_error_message(response)}")
    else:
        st.info("You are currently on the Free plan.")
        st.page_link("pages/pricing.py", label="🚀 Upgrade to Pro")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔄 Refresh profile", use_container_width=True):
            maybe_refresh_profile(force=True)
            st.rerun()

    with col2:
        if st.button("🚪 Logout", use_container_width=True):
            clear_auth()
            st.rerun()


def build_navigation():
    pages: dict[str, list] = {
        "TalentMatch Pro": [
            st.Page(
                dashboard_page,
                title="Dashboard",
                icon="🏠",
                default=True,
            ),
            st.Page(
                "pages/ats_checker.py",
                title="ATS Checker",
                icon="📄",
                url_path="ats_checker",
            ),
            st.Page(
                "pages/cv_rewrite.py",
                title="CV Rewrite",
                icon="✍️",
                url_path="cv_rewrite",
            ),
            st.Page(
                "pages/semantic_match.py",
                title="Semantic Match",
                icon="🎯",
                url_path="semantic_match",
            ),
            st.Page(
                "pages/recruiter_mode.py",
                title="Recruiter Mode",
                icon="👥",
                url_path="recruiter_mode",
            ),
            st.Page(
                "pages/history.py",
                title="History",
                icon="📜",
                url_path="history",
            ),
            st.Page(
                "pages/pricing.py",
                title="Pricing",
                icon="💳",
                url_path="pricing",
            ),
            st.Page(
                account_page,
                title="Account",
                icon="⚙️",
                url_path="account",
            ),
        ],
        "Authentication": [
            st.Page(
                "pages/login.py",
                title="Login",
                icon="🔐",
                url_path="login",
            ),
            st.Page(
                "pages/register.py",
                title="Register",
                icon="📝",
                url_path="register",
            ),
        ],
        "Legal": [],
    }

    terms_page = BASE_DIR / "pages" / "Terms.py"
    privacy_page = BASE_DIR / "pages" / "Privacy.py"
    refund_page = BASE_DIR / "pages" / "Refund.py"

    if terms_page.exists():
        pages["Legal"].append(
            st.Page(
                "pages/Terms.py",
                title="Terms",
                icon="📃",
                url_path="Terms",
            )
        )

    if privacy_page.exists():
        pages["Legal"].append(
            st.Page(
                "pages/Privacy.py",
                title="Privacy",
                icon="🔒",
                url_path="Privacy",
            )
        )

    if refund_page.exists():
        pages["Legal"].append(
            st.Page(
                "pages/Refund.py",
                title="Refund",
                icon="💸",
                url_path="Refund",
            )
        )

    if is_admin_user() and (BASE_DIR / "pages" / "admin_analytics.py").exists():
        pages["Admin"] = [
            st.Page(
                "pages/admin_analytics.py",
                title="Admin Analytics",
                icon="📊",
                url_path="admin_analytics",
            )
        ]

    return pages


profile = maybe_refresh_profile()
is_pro = is_pro_user()

render_global_sidebar(profile, is_pro)

navigation = st.navigation(build_navigation(), position="sidebar")
navigation.run()
