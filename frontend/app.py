import os
from pathlib import Path
from typing import Any, Dict, Optional

import requests
import streamlit as st

from components.sidebar import render_sidebar
from pages.landing import render_landing


# ============================================================
# TalentMatch Pro - Frontend entrypoint
# Streamlit app with SEO / Open Graph / Google verification
# ============================================================

APP_NAME = "TalentMatch Pro"
APP_TAGLINE = "AI-powered CV analysis and ATS optimization"
APP_DESCRIPTION = (
    "TalentMatch Pro helps job seekers analyze CVs, improve ATS performance, "
    "compare CVs with job descriptions, rewrite CV content, and unlock recruiter-ready insights."
)

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "https://talentmatch-frontend-dejan.onrender.com",
).rstrip("/")

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "https://talentmatch-backend-1283.onrender.com",
).rstrip("/")

GOOGLE_SITE_VERIFICATION = os.getenv(
    "GOOGLE_SITE_VERIFICATION",
    "7aXd9xJ8kUJObrYVz7am3Ot14cVTVsNKCNLIhw_c0qY",
)

ASSETS_DIR = Path(__file__).parent / "assets"
LOGO_PATH = ASSETS_DIR / "logo.png"
FAVICON_PATH = ASSETS_DIR / "favicon.png"


# ------------------------------------------------------------
# Page config
# ------------------------------------------------------------

st.set_page_config(
    page_title="TalentMatch Pro | AI CV Analysis & ATS Optimization",
    page_icon=str(FAVICON_PATH) if FAVICON_PATH.exists() else "🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ------------------------------------------------------------
# SEO / Open Graph / Google Search Console verification
# ------------------------------------------------------------

st.markdown(
    f"""
    <meta name="google-site-verification" content="{GOOGLE_SITE_VERIFICATION}" />

    <meta name="description" content="{APP_DESCRIPTION}" />
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


# ------------------------------------------------------------
# Global styling
# ------------------------------------------------------------

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 3rem;
            padding-bottom: 3rem;
            max-width: 1180px;
        }

        h1, h2, h3 {
            letter-spacing: -0.03em;
        }

        [data-testid="stSidebar"] {
            background: #eef4fb;
        }

        [data-testid="stSidebar"] .block-container {
            padding-top: 2rem;
        }

        .tmp-muted {
            color: #758195;
        }

        .tmp-card {
            border: 1px solid rgba(49, 61, 87, 0.12);
            border-radius: 18px;
            padding: 1.25rem;
            background: rgba(255, 255, 255, 0.55);
        }

        .tmp-pill {
            display: inline-block;
            padding: 0.45rem 0.8rem;
            border-radius: 999px;
            background: #e8f2ff;
            color: #0b63ce;
            border: 1px solid #b9d7ff;
            font-weight: 700;
        }

        footer {
            visibility: hidden;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# Backend helpers
# ------------------------------------------------------------

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
        return

    st.session_state["user"] = profile
    st.session_state["email"] = profile.get("email")
    st.session_state["user_id"] = profile.get("id") or profile.get("user_id")
    st.session_state["plan"] = profile.get("plan", "free")
    st.session_state["is_pro"] = bool(profile.get("is_pro") or profile.get("plan") == "pro")


def logout() -> None:
    for key in [
        "access_token",
        "token",
        "user",
        "email",
        "user_id",
        "plan",
        "is_pro",
        "is_admin",
    ]:
        st.session_state.pop(key, None)
    st.rerun()


# ------------------------------------------------------------
# Session defaults
# ------------------------------------------------------------

if "plan" not in st.session_state:
    st.session_state["plan"] = "free"

if "is_pro" not in st.session_state:
    st.session_state["is_pro"] = False

if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False


# ------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------


render_sidebar()


# ------------------------------------------------------------
# Main page
# ------------------------------------------------------------

render_landing()