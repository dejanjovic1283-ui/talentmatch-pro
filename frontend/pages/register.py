from __future__ import annotations

from html import escape

import streamlit as st

from auth_utils import (
    FIREBASE_API_KEY,
    begin_persistent_session,
    firebase_register,
    is_logged_in,
    logout_and_redirect,
    save_auth,
)
from components.sidebar import render_sidebar
from components.ui import apply_global_styles, render_hero, safe_html


st.set_page_config(
    page_title="Create Account • TalentMatch Pro",
    page_icon="📝",
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
            <div class="tm-kicker">{safe_html(icon)} TalentMatch Pro</div>
            <div class="tm-card-title">{safe_html(title)}</div>
            <div class="tm-muted">{safe_html(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


render_hero(
    "Create your account",
    "Start your TalentMatch Pro workspace",
    "Create a free account for ATS analysis, CV improvements, secure reports and a persistent browser session.",
    "🚀",
)

if is_logged_in():
    email = _current_email()
    persistent_session_notice = str(
        st.session_state.pop("persistent_session_notice", "") or ""
    ).strip()

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

    if persistent_session_notice:
        st.warning(persistent_session_notice)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏠 Go to Dashboard", use_container_width=True):
            st.switch_page("app.py")
    with col2:
        if st.button("🚪 Logout", use_container_width=True):
            logout_and_redirect()

    st.stop()

left, right = st.columns([1.05, 0.95])

with left:
    st.markdown(
        '<div class="tm-section-title">Create a free account</div>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        full_name = st.text_input(
            "Full name",
            placeholder="Dejan Jovic",
            autocomplete="name",
        )
        email = st.text_input(
            "Email address",
            placeholder="you@example.com",
            autocomplete="email",
        )
        password = st.text_input(
            "Password",
            type="password",
            placeholder="At least 6 characters",
            autocomplete="new-password",
        )
        password_confirm = st.text_input(
            "Confirm password",
            type="password",
            placeholder="Repeat your password",
            autocomplete="new-password",
        )

        st.caption(
            "After registration, confirm the secure browser session once. Your Firebase refresh token is stored only by the backend."
        )

        if st.button("🚀 Create Account", use_container_width=True, type="primary"):
            name_clean = " ".join(full_name.split()).strip()
            email_clean = email.strip().lower()

            if not FIREBASE_API_KEY:
                st.error("FIREBASE_API_KEY is missing in the environment variables.")
                st.stop()
            if len(name_clean) < 2 or len(name_clean) > 120:
                st.error("Enter your full name.")
                st.stop()
            if not email_clean or "@" not in email_clean:
                st.error("Enter a valid email address.")
                st.stop()
            if len(password) < 6:
                st.error("Password must contain at least 6 characters.")
                st.stop()
            if password != password_confirm:
                st.error("Passwords do not match.")
                st.stop()

            with st.spinner("Creating your account securely..."):
                data, error = firebase_register(
                    email_clean,
                    password,
                    name_clean,
                )

            if error:
                st.error(error)
                st.stop()

            if not data:
                st.error("Registration failed. Empty Firebase response.")
                st.stop()

            token = str(data.get("idToken") or "").strip()
            refresh_token = str(data.get("refreshToken") or "").strip()
            expires_in = data.get("expiresIn")

            if not token or not refresh_token or not expires_in:
                st.error("Registration failed. Firebase returned incomplete session data.")
                st.stop()

            save_auth(
                token=token,
                email=email_clean,
                full_name=name_clean,
                refresh_token=refresh_token,
                expires_in=expires_in,
            )

            activation_url, persistent_session_error = begin_persistent_session()
            if activation_url:
                safe_activation_url = escape(activation_url, quote=True)
                st.success("Account created. Confirm your secure browser session to continue.")
                st.markdown(
                    f"""
                    <a href="{safe_activation_url}" target="_self" rel="noreferrer"
                       style="display:block;text-align:center;padding:.8rem 1rem;border-radius:.7rem;background:#2563eb;color:#fff;font-weight:700;text-decoration:none;margin-top:.7rem">
                        🔐 Continue securely
                    </a>
                    """,
                    unsafe_allow_html=True,
                )
                st.caption(
                    "This one-time confirmation finishes the secure sign-in and never exposes your Firebase refresh token."
                )
                st.stop()

            st.session_state["persistent_session_notice"] = (
                "Account created and signed in for this open session, but durable session setup is unavailable: "
                f"{persistent_session_error or 'please try again later.'}"
            )
            st.rerun()

with right:
    _auth_card(
        "A complete career workspace",
        "Use ATS Checker, CV Rewrite, Semantic Match, Recruiter Mode, history and branded report exports from one account.",
        "✨",
    )
    st.write("")
    _auth_card(
        "Already have an account?",
        "Sign in securely and restore your browser session after closing Chrome.",
        "🔐",
    )
    if st.button("🔐 Go to Login", use_container_width=True):
        st.switch_page("pages/login.py")
