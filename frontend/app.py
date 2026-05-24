import os
import json
import requests
import streamlit as st
import extra_streamlit_components as stx

st.set_page_config(page_title="TalentMatch Pro", page_icon="🚀", layout="wide")

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "https://talentmatch-backend-1283.onrender.com",
).rstrip("/")

cookie_manager = stx.CookieManager()


def restore_auth_from_cookies():
    token = cookie_manager.get("tm_id_token")
    email = cookie_manager.get("tm_email")
    refresh_token = cookie_manager.get("tm_refresh_token")

    if token:
        st.session_state["firebase_id_token"] = token
        st.session_state["id_token"] = token
        st.session_state["idToken"] = token
        st.session_state["token"] = token
        st.session_state["access_token"] = token

        st.session_state["user"] = {
            "email": email or "",
            "idToken": token,
            "id_token": token,
            "refreshToken": refresh_token or "",
            "refresh_token": refresh_token or "",
        }


def clear_auth():
    for key in [
        "user",
        "profile",
        "firebase_id_token",
        "id_token",
        "idToken",
        "token",
        "access_token",
        "refresh_token",
        "analysis_result",
        "last_uploaded_name",
        "last_job_description",
    ]:
        st.session_state.pop(key, None)

    cookie_manager.delete("tm_email")
    cookie_manager.delete("tm_id_token")
    cookie_manager.delete("tm_refresh_token")


def get_auth_token():
    restore_auth_from_cookies()

    token = (
        st.session_state.get("firebase_id_token")
        or st.session_state.get("id_token")
        or st.session_state.get("idToken")
        or st.session_state.get("token")
        or st.session_state.get("access_token")
    )

    user = st.session_state.get("user")

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
    return {"Authorization": f"Bearer {token}"} if token else {}


def api_get(path, timeout=30):
    return requests.get(
        f"{BACKEND_URL}{path}",
        headers=get_auth_headers(),
        timeout=timeout,
    )


def api_post(path, data=None, json_data=None, files=None, timeout=120):
    return requests.post(
        f"{BACKEND_URL}{path}",
        headers=get_auth_headers(),
        data=data,
        json=json_data,
        files=files,
        timeout=timeout,
    )


def load_profile():
    if not get_auth_token():
        return None

    try:
        response = api_get("/me")

        if response.status_code == 200:
            profile = response.json()
            st.session_state["profile"] = profile
            return profile

        return None

    except Exception:
        return None


def get_profile():
    return st.session_state.get("profile") or load_profile() or {}


def refresh_profile():
    st.session_state.pop("profile", None)
    return load_profile()


def is_logged_in():
    return bool(get_auth_token())


def is_pro_user():
    profile = get_profile()

    return bool(
        profile.get("is_pro")
        or profile.get("plan") == "pro"
        or profile.get("subscription_status") in ["active", "trialing"]
    )


def get_usage():
    profile = get_profile()

    used = int(profile.get("analyses_used", 0) or 0)
    limit = int(profile.get("free_limit", 3) or 3)
    remaining = int(profile.get("remaining", max(limit - used, 0)) or 0)

    return used, limit, remaining


def require_login():
    if not is_logged_in():
        st.warning("Please login first.")
        st.page_link("pages/login.py", label="🔐 Go to Login")
        st.stop()


def require_pro(feature_name="This feature"):
    if not is_pro_user():
        st.error(f"{feature_name} is a Pro feature.")
        st.page_link("pages/pricing.py", label="🚀 Upgrade to Pro")
        st.stop()


def render_sidebar_auth():
    with st.sidebar:
        st.divider()
        st.markdown("### Authentication")

        user = st.session_state.get("user")

        if is_logged_in() and isinstance(user, dict):
            st.success("Signed in as")
            st.write(user.get("email", ""))

            if st.button("Sign out", use_container_width=True):
                clear_auth()
                st.rerun()
        else:
            st.warning("Not signed in")

            if st.button("Login", use_container_width=True):
                st.switch_page("pages/login.py")


restore_auth_from_cookies()

if is_logged_in():
    load_profile()

render_sidebar_auth()

is_pro = is_pro_user()

st.markdown("# 🚀 TalentMatch Pro")
st.markdown("## AI-powered CV analysis for modern job seekers")
st.write("Optimize your CV, identify missing skills, improve ATS performance, and increase interview chances.")

st.caption("Plan: ⭐ PRO" if is_pro else "Plan: FREE")
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

if is_pro:
    st.success("🚀 Pro plan active — unlimited analyses and premium tools unlocked.")
else:
    used, limit, remaining = get_usage()
    st.info(f"Free plan: {used}/{limit} analyses used. Remaining: {remaining}")
    st.progress(min(used / limit, 1) if limit else 0)

uploaded_file = st.file_uploader("Upload your CV as a PDF", type=["pdf"])

if uploaded_file:
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
            data = {"job_description": job_description}

            response = api_post("/analyze", data=data, files=files)

            if response.status_code == 200:
                st.session_state["analysis_result"] = response.json()
                refresh_profile()
                st.success("Analysis completed successfully.")
                st.rerun()

            elif response.status_code == 403:
                st.error("Free limit reached or Pro required.")
                st.page_link("pages/pricing.py", label="🚀 Upgrade to Pro")

            else:
                st.error(f"Analysis failed: {response.status_code}")
                st.code(response.text)

        except Exception as exc:
            st.error(f"Analysis failed: {exc}")

if uploaded_file is None:
    st.info("Upload a PDF CV to start.")

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
            st.button("📄 Generate PDF Report", use_container_width=True)
        else:
            st.button("📄 Generate PDF Report (Pro)", use_container_width=True, disabled=True)
            st.caption("Upgrade to Pro to export PDF reports.")

    st.divider()

    st.markdown("## 📝 Summary")
    st.write(result.get("summary", "No summary available."))

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("## ✅ Strengths")
        for item in result.get("strengths", []):
            st.markdown(f"- {item}")

    with col2:
        st.markdown("## ❌ Missing Skills")
        for item in result.get("missing_skills", []):
            st.markdown(f"- {item}")

    st.markdown("## 💡 Recommendations")
    for item in result.get("recommendations", []):
        st.markdown(f"- {item}")