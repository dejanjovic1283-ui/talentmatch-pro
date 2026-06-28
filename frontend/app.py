import os
from pathlib import Path

import streamlit as st

from components.sidebar import render_sidebar
from components.ui import apply_global_styles
from pages.landing import render_landing


APP_DESCRIPTION = (
    "TalentMatch Pro helps job seekers analyze CVs, improve ATS performance, "
    "compare CVs with job descriptions, rewrite CV content, and unlock recruiter-ready insights."
)

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://talentmatchcv.com").rstrip("/")
GOOGLE_SITE_VERIFICATION = os.getenv(
    "GOOGLE_SITE_VERIFICATION",
    "7aXd9xJ8kUJObrYVz7am3Ot14cVTVsNKCNLIhw_c0qY",
)

ASSETS_DIR = Path(__file__).parent / "assets"
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
    <meta name="robots" content="index, follow" />
    <link rel="canonical" href="{FRONTEND_URL}/" />

    <meta property="og:type" content="website" />
    <meta property="og:title" content="TalentMatch Pro | AI CV Analysis & ATS Optimization" />
    <meta property="og:description" content="{APP_DESCRIPTION}" />
    <meta property="og:url" content="{FRONTEND_URL}/" />
    <meta property="og:site_name" content="TalentMatch Pro" />
    <meta property="og:image" content="{FRONTEND_URL}/app/static/logo.png" />
    """,
    unsafe_allow_html=True,
)

if "plan" not in st.session_state:
    st.session_state["plan"] = "free"
if "is_pro" not in st.session_state:
    st.session_state["is_pro"] = False
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False

apply_global_styles()
render_sidebar()
render_landing()
