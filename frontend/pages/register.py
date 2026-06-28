from __future__ import annotations

import time
from typing import Optional

import requests
import streamlit as st

from auth_utils import FIREBASE_API_KEY, is_logged_in, save_auth
from components.sidebar import render_sidebar
from components.ui import apply_global_styles, render_hero, safe_html


st.set_page_config(
    page_title="Register • TalentMatch Pro",
    page_icon="🚀",
    layout="wide",
)

apply_global_styles()
render_sidebar()


def firebase_register(email: str, password: str, full_name: str = "") -> tuple[dict | None, str | None]:
    """Create a Firebase account and optionally store displayName."""
    if not FIREBASE_API_KEY:
        return None, "FIREBASE_API_KEY is missing in Render Environment."

    signup_url = (
        "https://identitytoolkit.googleapis.com/v1/accounts:"
        f"signUp?key={FIREBASE_API_KEY}"
    )

    signup_payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }

    try:
        response = requests.post(signup_url, json=signup_payload, timeout=60)
    except requests.RequestException as exc:
        return None, f"Firebase request failed: {exc}"

    if response.status_code != 200:
        try:
            error_message = response.json().get("error", {}).get("message", response.text)
        except Exception:
            error_message = response.text
        return None, error_message

    try:
        data = response.json()
    except Exception:
        return None, "Firebase returned invalid JSON."

    display_name = full_name.strip()
    token = str(data.get("idToken") or "").strip()

    if display_name and token:
        update_url = (
            "https://identitytoolkit.googleapis.com/v1/accounts:"
            f"update?key={FIREBASE_API_KEY}"
        )
        update_payload = {
            "idToken": token,
            "displayName": display_name,
            "returnSecureToken": True,
        }

        try:
            update_response = requests.post(update_url, json=update_payload, timeout=60)
            if update_response.status_code == 200:
                updated_data = update_response.json()
                if isinstance(updated_data, dict):
                    data.update(updated_data)
                    data["displayName"] = display_name
        except Exception:
            data["displayName"] = display_name

    return data, None


def _current_email() -> str:
    user = st.session_state.get("user")
    user_email = user.get("email", "") if isinstance(user, dict) else ""
    return str(
        st.session_state.get("email")
        or st.session_state.get("user_email")
        or user_email
        or ""
    ).strip()


def _benefit_card(icon: str, title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="tm-card" style="height:100%">
            <div style="font-size:1.8rem;margin-bottom:.4rem">{safe_html(icon)}</div>
            <div class="tm-card-title">{safe_html(title)}</div>
            <div class="tm-muted">{safe_html(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


render_hero(
    "Create your workspace",
    "Start using TalentMatch Pro",
    "Create a free account and get instant access to AI-powered CV analysis, ATS checks and your personal report history.",
    "🚀",
)

if is_logged_in():
    email = _current_email()

    st.markdown(
        f"""
        <div class="tm-card" style="margin-top:1rem">
            <div class="tm-kicker">✅ Active account</div>
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
        if st.button("💳 View Pricing", use_container_width=True):
            st.switch_page("pages/pricing.py")

    st.stop()

left, right = st.columns([1.05, 0.95])

with left:
    st.markdown('<div class="tm-section-title">Create account</div>', unsafe_allow_html=True)

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
            placeholder="Minimum 6 characters",
            autocomplete="new-password",
        )
        confirm_password = st.text_input(
            "Confirm password",
            type="password",
            placeholder="Repeat your password",
            autocomplete="new-password",
        )

        st.caption("Your full name is used for a professional welcome message and account profile display.")

        if st.button("🚀 Create Account", use_container_width=True, type="primary"):
            full_name_clean = full_name.strip()
            email_clean = email.strip().lower()

            if not full_name_clean or not email_clean or not password or not confirm_password:
                st.error("Please fill all fields.")
                st.stop()

            if password != confirm_password:
                st.error("Passwords do not match.")
                st.stop()

            if len(password) < 6:
                st.error("Password must be at least 6 characters.")
                st.stop()

            with st.spinner("Creating your TalentMatch workspace..."):
                data, error = firebase_register(email_clean, password, full_name_clean)

            if error:
                st.error(error)
                st.stop()

            if not data:
                st.error("Registration failed. Empty Firebase response.")
                st.stop()

            token = data.get("idToken", "")

            if not token:
                st.error("Registration failed. Firebase did not return idToken.")
                st.stop()

            save_auth(token=token, email=email_clean)
            st.session_state["full_name"] = full_name_clean
            user_state = st.session_state.get("user")
            if isinstance(user_state, dict):
                user_state["full_name"] = full_name_clean
                st.session_state["user"] = user_state

            st.success("Account created successfully.")
            st.info("You can now use ATS Checker, CV Analysis and your personal History dashboard.")
            time.sleep(0.8)
            st.rerun()

with right:
    cols = st.columns(2)
    with cols[0]:
        _benefit_card("🎯", "ATS ready", "Check keyword coverage before applying.")
    with cols[1]:
        _benefit_card("🧠", "Semantic AI", "Compare CV meaning against real jobs.")

    cols = st.columns(2)
    with cols[0]:
        _benefit_card("📜", "History", "Save and revisit previous analyses.")
    with cols[1]:
        _benefit_card("📄", "Reports", "Export polished TalentMatch PDF reports.")

    st.write("")
    if st.button("🔐 Already have an account? Login", use_container_width=True):
        st.switch_page("pages/login.py")
