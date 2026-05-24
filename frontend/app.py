import os
import json
import time
import requests
import streamlit as st


# ------------------------------------------------------------
# Config
# ------------------------------------------------------------

def load_config():
    backend_url = (
        os.getenv("BACKEND_URL")
        or st.secrets.get("BACKEND_URL", "")
        or "https://talentmatch-backend-1283.onrender.com"
    )

    return {
        "backend_url": backend_url.rstrip("/")
    }


CONFIG = load_config()
BACKEND_URL = CONFIG["backend_url"]


# ------------------------------------------------------------
# Auth helpers
# ------------------------------------------------------------

def get_current_user():
    return st.session_state.get("user")


def get_auth_token():
    token = (
        st.session_state.get("firebase_id_token")
        or st.session_state.get("id_token")
        or st.session_state.get("token")
        or st.session_state.get("access_token")
    )

    user = st.session_state.get("user") or {}

    if not token and isinstance(user, dict):
        token = (
            user.get("idToken")
            or user.get("id_token")
            or user.get("token")
            or user.get("accessToken")
            or user.get("access_token")
        )

    return token


def get_auth_headers():
    token = get_auth_token()

    if token:
        return {
            "Authorization": f"Bearer {token}"
        }

    return {}


def api_get(path, timeout=20):
    url = f"{BACKEND_URL}{path}"
    return requests.get(url, headers=get_auth_headers(), timeout=timeout)


def api_post(path, data=None, json_data=None, files=None, timeout=60):
    url = f"{BACKEND_URL}{path}"
    return requests.post(
        url,
        headers=get_auth_headers(),
        data=data,
        json=json_data,
        files=files,
        timeout=timeout,
    )


# ------------------------------------------------------------
# Profile / plan helpers
# ------------------------------------------------------------

def load_profile():
    try:
        res = api_get("/me")

        if res.status_code == 200:
            profile = res.json()
            st.session_state["profile"] = profile
            return profile

        return None

    except Exception:
        return None


def refresh_profile():
    profile = load_profile()
    return profile


def get_profile():
    return st.session_state.get("profile") or load_profile() or {}


def is_pro_user():
    profile = get_profile()

    return bool(
        profile.get("is_pro")
        or profile.get("plan") == "pro"
        or profile.get("subscription_status") in ["active", "trialing"]
    )


def get_plan_label():
    return "PRO" if is_pro_user() else "FREE"


def get_usage():
    profile = get_profile()

    used = int(profile.get("analyses_used", 0) or 0)
    limit = int(profile.get("free_limit", 3) or 3)
    remaining = int(profile.get("remaining", max(limit - used, 0)) or 0)

    return used, limit, remaining


# ------------------------------------------------------------
# UI helpers
# ------------------------------------------------------------

def render_header():
    is_pro = is_pro_user()
    plan = get_plan_label()

    st.markdown("# 🚀 TalentMatch Pro")
    st.markdown("## AI-powered CV analysis for modern job seekers")
    st.write(
        "Optimize your CV, identify missing skills, improve ATS performance, "
        "and increase interview chances."
    )

    if is_pro:
        st.caption("Plan: ⭐ PRO")
    else:
        st.caption("Plan: FREE")

    st.caption("AI-powered CV matching, ATS keyword analysis, and job application insights.")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.caption("AI CV Match")
        st.markdown("### GPT Powered")

    with col2:
        st.caption("ATS Scanner")
        st.markdown("### Built In")

    with col3:
        st.caption("Semantic Match")
        st.markdown("### Enabled" if is_pro else "### Upgrade")

    with col4:
        st.caption("Recruiter Mode")
        st.markdown("### Enabled" if is_pro else "### Upgrade")

    st.divider()


def render_usage_banner():
    if is_pro_user():
        st.success("🚀 Pro plan active — unlimited analyses and premium tools unlocked.")
        return

    used, limit, remaining = get_usage()

    st.info(f"Free plan: {used}/{limit} analyses used. Remaining: {remaining}")

    progress = 0
    if limit > 0:
        progress = min(used / limit, 1)

    st.progress(progress)


def render_auth_box():
    user = st.session_state.get("user")

    with st.sidebar:
        st.divider()
        st.markdown("### Authentication")

        if user:
            email = user.get("email") if isinstance(user, dict) else str(user)
            st.success("Signed in as")
            st.write(email)

            if st.button("Sign out", use_container_width=True):
                for key in [
                    "user",
                    "profile",
                    "firebase_id_token",
                    "id_token",
                    "token",
                    "access_token",
                    "analysis_result",
                    "last_uploaded_name",
                    "last_job_description",
                ]:
                    st.session_state.pop(key, None)

                st.rerun()
        else:
            st.warning("Not signed in")
            if st.button("Login", use_container_width=True):
                st.switch_page("pages/login.py")


def require_login():
    if not st.session_state.get("user"):
        st.warning("Please login first.")
        st.page_link("pages/login.py", label="Go to Login")
        st.stop()


def require_pro(feature_name="This feature"):
    if not is_pro_user():
        st.error(f"{feature_name} is a Pro feature.")
        st.warning(f"🚀 {feature_name} is a Pro feature.")
        st.page_link("pages/pricing.py", label="🚀 Upgrade to Pro")
        st.stop()


# ------------------------------------------------------------
# Main app
# ------------------------------------------------------------

st.set_page_config(
    page_title="TalentMatch Pro",
    page_icon="🚀",
    layout="wide",
)

render_auth_box()

# Auto refresh profile on page load if logged in
if st.session_state.get("user"):
    refresh_profile()

render_header()
render_usage_banner()

uploaded_file = st.file_uploader(
    "Upload your CV as a PDF",
    type=["pdf"],
    help="Upload a PDF CV to analyze against a job description.",
)

if uploaded_file is not None:
    st.session_state["last_uploaded_name"] = uploaded_file.name
    st.info(f"Selected file: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")

job_description = st.text_area(
    "Paste the job description",
    value=st.session_state.get("last_job_description", ""),
    placeholder=(
        "Paste the job description here...\n\n"
        "Example:\n\n"
        "Senior Backend Engineer\n\n"
        "Requirements:\n"
        "• Python\n"
        "• FastAPI\n"
        "• PostgreSQL\n"
        "• Cloud deployment"
    ),
    height=260,
)

st.session_state["last_job_description"] = job_description

can_analyze = uploaded_file is not None and job_description.strip()

if st.button("Analyze CV", use_container_width=True, disabled=not can_analyze):
    require_login()

    with st.spinner("Analyzing CV..."):
        try:
            files = {
                "file": (
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    "application/pdf",
                )
            }

            data = {
                "job_description": job_description
            }

            res = api_post(
                "/analyze",
                data=data,
                files=files,
                timeout=120,
            )

            if res.status_code == 200:
                result = res.json()
                st.session_state["analysis_result"] = result

                refresh_profile()

                st.success("Analysis completed successfully.")
                st.rerun()

            elif res.status_code == 403:
                st.error("Free limit reached or Pro required.")
                st.page_link("pages/pricing.py", label="Upgrade to Pro")

            else:
                st.error(f"Analysis failed: {res.status_code}")
                st.code(res.text)

        except Exception as e:
            st.error(f"Analysis failed: {e}")


if uploaded_file is None:
    st.info("Upload a PDF CV to start.")


# ------------------------------------------------------------
# Results
# ------------------------------------------------------------

result = st.session_state.get("analysis_result")

if result:
    st.divider()
    st.markdown("## Analysis result")

    score = result.get("score") or result.get("match_score") or 0
    verdict = result.get("verdict") or "Match result"
    cv_file = result.get("cv_file") or st.session_state.get("last_uploaded_name", "CV")

    st.success(f"🔥 {verdict} — {score}/100")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.caption("Match Score")
        st.markdown(f"## {score}/100")

    with col2:
        st.caption("Verdict")
        st.markdown(f"## {verdict}")

    with col3:
        st.caption("CV file")
        st.markdown(f"## {cv_file}")

    try:
        st.progress(min(int(score) / 100, 1))
    except Exception:
        pass

    report_text = result.get("report_text") or json.dumps(result, indent=2)

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            "📥 Download TXT Report",
            data=report_text,
            file_name="talentmatch_report.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with col2:
        if is_pro_user():
            if st.button("📄 Generate PDF Report", use_container_width=True):
                st.info("PDF report generation endpoint can be connected here.")
        else:
            st.button(
                "📄 Generate PDF Report (Pro)",
                use_container_width=True,
                disabled=True,
            )
            st.caption("Upgrade to Pro to export PDF reports.")

    st.divider()

    st.markdown("## 📝 Summary")
    st.write(result.get("summary", "No summary available."))

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("## ✅ Strengths")
        strengths = result.get("strengths", [])
        if isinstance(strengths, list) and strengths:
            for item in strengths:
                st.markdown(f"- {item}")
        else:
            st.write("No strengths returned.")

    with col2:
        st.markdown("## ❌ Missing Skills")
        missing = result.get("missing_skills", [])
        if isinstance(missing, list) and missing:
            for item in missing:
                st.markdown(f"- {item}")
        else:
            st.write("No missing skills returned.")

    st.markdown("## 💡 Recommendations")
    recommendations = result.get("recommendations", [])
    if isinstance(recommendations, list) and recommendations:
        for item in recommendations:
            st.markdown(f"- {item}")
    else:
        st.write("No recommendations returned.")