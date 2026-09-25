from __future__ import annotations

from html import escape

import streamlit as st

from auth_utils import (
    FIREBASE_API_KEY,
    begin_persistent_session,
    firebase_login,
    is_logged_in,
    logout_and_redirect,
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

        if st.button("🔄 Retry secure session", use_container_width=True):
            with st.spinner("Retrying secure session..."):
                retry_activation_url, retry_error = begin_persistent_session()

            if retry_activation_url:
                safe_activation_url = escape(
                    retry_activation_url,
                    quote=True,
                )
                st.success(
                    "Secure session setup is ready. Confirm it to continue."
                )
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
                "Secure session setup is still unavailable: "
                f"{retry_error or 'please try again later.'}"
            )
            st.rerun()

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

        st.caption(
            "After sign-in, you will confirm a secure browser session that can be restored automatically."
        )

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

            token = str(data.get("idToken") or "").strip()
            refresh_token = str(data.get("refreshToken") or "").strip()
            expires_in = data.get("expiresIn")

            if not token or not refresh_token or not expires_in:
                st.error("Login failed. Firebase returned incomplete session data.")
                st.stop()

            save_auth(
                token=token,
                email=email_clean,
                refresh_token=refresh_token,
                expires_in=expires_in,
            )

            display_name = str(data.get("displayName") or "").strip()
            if display_name:
                st.session_state["full_name"] = display_name
                user_state = st.session_state.get("user")
                if isinstance(user_state, dict):
                    user_state["full_name"] = display_name
                    st.session_state["user"] = user_state

            activation_url, persistent_session_error = begin_persistent_session()
            if activation_url:
                safe_activation_url = escape(activation_url, quote=True)
                st.success("Login successful. Confirm your secure browser session to continue.")
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
                "Login succeeded for this open session, but durable session setup is unavailable: "
                f"{persistent_session_error or 'please try again later.'}"
            )
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
