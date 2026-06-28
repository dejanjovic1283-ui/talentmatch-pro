from __future__ import annotations

import time

import streamlit as st

from auth_utils import (
    FIREBASE_API_KEY,
    clear_auth,
    firebase_login,
    is_logged_in,
    save_auth,
)
from components.sidebar import render_sidebar
from components.ui import apply_global_styles, render_hero, safe_html


st.set_page_config(
    page_title="Login • TalentMatch Pro",
    page_icon="🔐",
    layout="wide",
)

apply_global_styles()
render_sidebar()


def _current_email() -> str:
    user = st.session_state.get("user")
    user_email = user.get("email", "") if isinstance(user, dict) else ""
    return str(
        st.session_state.get("email")
        or st.session_state.get("user_email")
        or user_email
        or ""
    ).strip()


def _auth_card(title: str, body: str, icon: str) -> None:
    st.markdown(
        f"""
        <div class="tm-card" style="height:100%">
            <div class="tm-kicker">{safe_html(icon)} Secure access</div>
            <div class="tm-card-title">{safe_html(title)}</div>
            <div class="tm-muted">{safe_html(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


render_hero(
    "Welcome back",
    "Login to TalentMatch Pro",
    "Continue improving CVs, checking ATS keyword coverage, exporting branded reports and managing your Pro workspace.",
    "🔐",
)

if is_logged_in():
    email = _current_email()

    st.markdown(
        f"""
        <div class="tm-card" style="margin-top:1rem">
            <div class="tm-kicker">✅ Active session</div>
            <div class="tm-card-title">You are already logged in</div>
            <div class="tm-muted">Signed in as <b>{safe_html(email or 'your TalentMatch account')}</b>.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏠 Go to Dashboard", use_container_width=True):
            st.switch_page("app.py")
    with col2:
        if st.button("🚪 Logout", use_container_width=True):
            clear_auth()
            st.rerun()

    st.stop()

left, right = st.columns([1.05, 0.95])

with left:
    st.markdown('<div class="tm-section-title">Sign in</div>', unsafe_allow_html=True)

    with st.container(border=True):
        email = st.text_input(
            "Email address",
            placeholder="you@example.com",
            autocomplete="email",
        )
        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter your password",
            autocomplete="current-password",
        )

        remember_note = st.caption("Your session is stored only in this browser session state.")

        if st.button("🔐 Login", use_container_width=True, type="primary"):
            email_clean = email.strip().lower()

            if not FIREBASE_API_KEY:
                st.error("FIREBASE_API_KEY is missing in Render environment variables.")
                st.stop()

            if not email_clean or not password:
                st.error("Enter email and password.")
                st.stop()

            with st.spinner("Logging in securely..."):
                data, error = firebase_login(email_clean, password)

            if error:
                st.error(error)
                st.stop()

            if not data:
                st.error("Login failed. Empty Firebase response.")
                st.stop()

            token = data.get("idToken", "")

            if not token:
                st.error("Login failed. Firebase did not return idToken.")
                st.stop()

            save_auth(token=token, email=email_clean)

            display_name = str(data.get("displayName") or "").strip()
            if display_name:
                st.session_state["full_name"] = display_name
                user_state = st.session_state.get("user")
                if isinstance(user_state, dict):
                    user_state["full_name"] = display_name
                    st.session_state["user"] = user_state

            st.success("Login successful.")
            time.sleep(0.8)
            st.rerun()

with right:
    _auth_card(
        "Enterprise-style CV workspace",
        "Access ATS Checker, CV Rewrite, Semantic Match, Recruiter Mode, history and branded report exports from one polished dashboard.",
        "✨",
    )
    st.write("")
    _auth_card(
        "New here?",
        "Create a free account and upgrade to Pro when you need premium matching, recruiter ranking and PDF exports.",
        "🚀",
    )
    if st.button("🚀 Create Account", use_container_width=True):
        st.switch_page("pages/register.py")
