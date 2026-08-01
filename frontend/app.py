from __future__ import annotations

import os
from html import escape
from pathlib import Path

import streamlit as st

from components.sidebar import render_sidebar
from components.ui import apply_global_styles
from i18n import get_seo, init_i18n
from pages.landing import render_landing


FRONTEND_URL = os.getenv("FRONTEND_URL", "https://talentmatchcv.com").rstrip("/")
GOOGLE_SITE_VERIFICATION = os.getenv(
    "GOOGLE_SITE_VERIFICATION",
    "7aXd9xJ8kUJObrYVz7am3Ot14cVTVsNKCNLIhw_c0qY",
).strip()

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
FAVICON_PATH = ASSETS_DIR / "favicon.png"

locale = init_i18n()
seo = get_seo(locale)

st.set_page_config(
    page_title=seo["title"],
    page_icon=str(FAVICON_PATH) if FAVICON_PATH.exists() else "🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

verification_meta = (
    f'<meta name="google-site-verification" content="{escape(GOOGLE_SITE_VERIFICATION, quote=True)}" />'
    if GOOGLE_SITE_VERIFICATION
    else ""
)

st.markdown(
    (
        f'{verification_meta}'
        f'<meta name="description" content="{escape(seo["description"], quote=True)}" />'
        f'<meta name="keywords" content="{escape(seo["keywords"], quote=True)}" />'
        '<meta name="robots" content="index, follow" />'
        f'<meta http-equiv="content-language" content="{escape(seo["html_lang"], quote=True)}" />'
        f'<link rel="canonical" href="{escape(FRONTEND_URL + "/", quote=True)}" />'
        '<meta property="og:type" content="website" />'
        f'<meta property="og:title" content="{escape(seo["title"], quote=True)}" />'
        f'<meta property="og:description" content="{escape(seo["description"], quote=True)}" />'
        f'<meta property="og:url" content="{escape(FRONTEND_URL + "/", quote=True)}" />'
        '<meta property="og:site_name" content="TalentMatch Pro" />'
        f'<meta property="og:image" content="{escape(FRONTEND_URL + "/app/static/logo.png", quote=True)}" />'
    ),
    unsafe_allow_html=True,
)

st.session_state.setdefault("plan", "free")
st.session_state.setdefault("is_pro", False)
st.session_state.setdefault("is_admin", False)

apply_global_styles()
render_sidebar()
render_landing()
