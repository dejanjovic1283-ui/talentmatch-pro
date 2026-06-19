import os
from pathlib import Path
from typing import Any, Dict, Optional

import requests
import streamlit as st

try:
    from components.sidebar import render_sidebar
except Exception:
    render_sidebar = None

APP_NAME = "TalentMatch Pro"
APP_TAGLINE = "AI-powered CV analysis and ATS optimization"
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://talentmatch-frontend-dejan.onrender.com").rstrip("/")
BACKEND_URL = os.getenv("BACKEND_URL", "https://talentmatch-backend-1283.onrender.com").rstrip("/")
GOOGLE_SITE_VERIFICATION = os.getenv("GOOGLE_SITE_VERIFICATION", "7aXd9xJ8kUJObrYVz7am3Ot14cVTVsNKCNLIhw_c0qY")
APP_DESCRIPTION = (
    "TalentMatch Pro is an AI-powered CV analysis platform for ATS optimization, "
    "semantic matching, CV rewrite suggestions, recruiter workflows, PDF reports, "
    "and PayPal-powered subscriptions."
)
APP_KEYWORDS = (
    "AI CV analysis, ATS checker, CV optimization, resume analysis, semantic matching, "
    "CV rewrite, recruiter mode, PDF reports, PayPal billing"
)

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "logo.png"
FAVICON_PATH = ASSETS_DIR / "favicon.png"

st.set_page_config(
    page_title="TalentMatch Pro | AI CV Analysis & ATS Optimization",
    page_icon=str(FAVICON_PATH) if FAVICON_PATH.exists() else "🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    f"""
    <meta name="google-site-verification" content="{GOOGLE_SITE_VERIFICATION}" />
    <meta name="description" content="{APP_DESCRIPTION}" />
    <meta name="keywords" content="{APP_KEYWORDS}" />
    <meta name="author" content="TalentMatch Pro" />
    <meta name="robots" content="index, follow" />
    <link rel="canonical" href="{FRONTEND_URL}/" />
    <meta property="og:type" content="website" />
    <meta property="og:title" content="TalentMatch Pro | AI CV Analysis & ATS Optimization" />
    <meta property="og:description" content="{APP_DESCRIPTION}" />
    <meta property="og:url" content="{FRONTEND_URL}/" />
    <meta property="og:site_name" content="TalentMatch Pro" />
    <meta property="og:image" content="{FRONTEND_URL}/app/static/logo.png" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="TalentMatch Pro | AI CV Analysis & ATS Optimization" />
    <meta name="twitter:description" content="{APP_DESCRIPTION}" />
    <meta name="twitter:image" content="{FRONTEND_URL}/app/static/logo.png" />
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
        .block-container {max-width: 1180px; padding-top: 2.8rem; padding-bottom: 3rem;}
        h1, h2, h3 {letter-spacing: -0.03em;}
        [data-testid="stSidebar"] {background: #eef4fb;}
        .tmp-muted {color: #6b7280;}
        .tmp-card {border: 1px solid rgba(49,61,87,.14); border-radius: 18px; padding: 1.2rem; background: rgba(255,255,255,.62); min-height: 150px;}
        .tmp-footer {color: #8b95a7; font-size: .92rem; padding-top: 1.5rem;}
        footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)


def api_url(path: str) -> str:
    clean_path = path if path.startswith("/") else f"/{path}"
    return f"{BACKEND_URL}{clean_path}"


def get_auth_headers() -> Dict[str, str]:
    token = st.session_state.get("access_token") or st.session_state.get("token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def safe_get(path: str, timeout: int = 20) -> Optional[Dict[str, Any]]:
    try:
        response = requests.get(api_url(path), headers=get_auth_headers(), timeout=timeout)
        if response.status_code != 200:
            return None
        return response.json()
    except Exception:
        return None


def refresh_profile() -> None:
    profile = safe_get("/me")
    if not profile:
        st.warning("Profile could not be refreshed right now.")
        return
    st.session_state["user"] = profile
    st.session_state["email"] = profile.get("email")
    st.session_state["user_id"] = profile.get("id") or profile.get("user_id")
    st.session_state["plan"] = profile.get("plan", "free")
    st.session_state["is_pro"] = bool(profile.get("is_pro") or profile.get("plan") == "pro")
    st.success("Profile refreshed.")


def logout() -> None:
    for key in ["access_token", "token", "user", "email", "user_id", "plan", "is_pro", "is_admin"]:
        st.session_state.pop(key, None)
    st.rerun()


def ensure_session_defaults() -> None:
    st.session_state.setdefault("plan", "free")
    st.session_state.setdefault("is_pro", False)
    st.session_state.setdefault("is_admin", False)


def render_fallback_sidebar() -> None:
    with st.sidebar:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), use_container_width=True)
        st.markdown("## 🎯 TalentMatch Pro")
        st.caption(APP_TAGLINE)
        st.divider()
        st.page_link("app.py", label="Dashboard", icon="🏠")
        st.page_link("pages/ats_checker.py", label="ATS Checker", icon="📄")
        st.page_link("pages/cv_rewrite.py", label="CV Rewrite", icon="✍️")
        st.page_link("pages/semantic_match.py", label="Semantic Match", icon="🎯")
        st.page_link("pages/recruiter_mode.py", label="Recruiter Mode", icon="👥")
        st.page_link("pages/history.py", label="History", icon="📜")
        st.page_link("pages/pricing.py", label="Pricing", icon="💳")
        st.page_link("pages/account.py", label="Account", icon="⚙️")
        st.divider()
        st.page_link("pages/terms.py", label="Terms", icon="📃")
        st.page_link("pages/privacy.py", label="Privacy", icon="🔒")
        st.page_link("pages/refund.py", label="Refund", icon="💸")
        if st.session_state.get("email"):
            st.divider()
            st.success(f"Signed in as\n\n{st.session_state.get('email')}")
            if st.button("🔄 Refresh profile", use_container_width=True):
                refresh_profile()
            if st.button("🚪 Logout", use_container_width=True):
                logout()


def render_app_sidebar() -> None:
    if render_sidebar is None:
        render_fallback_sidebar()
        return
    try:
        render_sidebar()
    except Exception:
        render_fallback_sidebar()


def render_dashboard() -> None:
    st.markdown(
        """
        <div style="padding:18px 0;">
            <h1 style="font-size:56px; margin-bottom:8px;">🚀 TalentMatch Pro</h1>
            <h2 style="font-size:28px; font-weight:650; margin-top:0;">AI-powered CV analysis for modern job seekers</h2>
            <p class="tmp-muted" style="font-size:18px; max-width:920px;">
                Optimize your CV, identify missing skills, improve ATS performance, and increase interview chances.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    is_pro = bool(st.session_state.get("is_pro"))
    if is_pro:
        st.success("Plan: PRO")
    else:
        st.info("Free plan: 0/3 analyses used. Remaining: 3")

    st.markdown("---")
    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric("AI CV Match", "GPT Powered")
    metric_2.metric("ATS Scanner", "Built In")
    metric_3.metric("Semantic Match", "Upgrade" if not is_pro else "Enabled")
    metric_4.metric("Recruiter Mode", "Upgrade" if not is_pro else "Enabled")

    st.markdown("---")
    st.markdown("## Start here")
    start_col_1, start_col_2, start_col_3 = st.columns(3)
    with start_col_1:
        with st.container(border=True):
            st.markdown("### 📄 ATS Checker")
            st.write("Check your CV against ATS-friendly keywords and basic structure.")
            st.page_link("pages/ats_checker.py", label="Open ATS Checker", icon="🎯")
    with start_col_2:
        with st.container(border=True):
            st.markdown("### ✍️ CV Rewrite")
            st.write("Rewrite CV summaries and bullet points for a specific job.")
            st.page_link("pages/cv_rewrite.py", label="Open CV Rewrite", icon="✍️")
    with start_col_3:
        with st.container(border=True):
            st.markdown("### 💳 Upgrade")
            st.write("Unlock unlimited analyses, PDF reports, semantic matching, and recruiter workflows.")
            st.page_link("pages/pricing.py", label="Upgrade with PayPal", icon="💳")

    st.markdown("---")
    st.markdown("## Pricing preview")
    free_col, pro_col = st.columns(2)
    with free_col:
        with st.container(border=True):
            st.markdown("### Free")
            st.markdown("## $0/month")
            st.write("✅ 3 CV analyses")
            st.write("✅ ATS Checker")
            st.write("✅ TXT Export")
            st.write("❌ PDF Reports")
            st.write("❌ CV Rewrite AI")
            st.write("❌ Semantic Match")
            st.write("❌ Recruiter Mode")
    with pro_col:
        with st.container(border=True):
            st.markdown("### Pro")
            st.markdown("## $9/month")
            st.write("✅ Unlimited CV Analyses")
            st.write("✅ PDF Reports")
            st.write("✅ CV Rewrite AI")
            st.write("✅ Semantic Match")
            st.write("✅ Recruiter Mode")
            st.write("✅ Candidate Ranking")
            st.write("✅ Saved History")
            st.info("Secure monthly subscription powered by PayPal.")
            st.page_link("pages/pricing.py", label="🚀 Upgrade to Pro with PayPal")

    st.markdown("---")
    footer_col_1, footer_col_2, footer_col_3 = st.columns(3)
    with footer_col_1:
        st.markdown("### 🎯 TalentMatch Pro")
        st.caption("AI-powered CV analysis, ATS optimization, semantic job matching, and recruiter-ready insights.")
    with footer_col_2:
        st.markdown("### 📬 Contact")
        st.caption("Email: support@talentmatchcv.com")
        st.caption("Country: Serbia")
    with footer_col_3:
        st.markdown("### 🔐 Legal")
        st.caption("Terms • Privacy • Refund")
        st.caption("Built for job seekers and recruiters.")
    st.markdown('<div class="tmp-footer">© 2026 TalentMatch Pro. All rights reserved.</div>', unsafe_allow_html=True)


ensure_session_defaults()
render_app_sidebar()
render_dashboard()