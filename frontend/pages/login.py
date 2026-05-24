import os
from datetime import datetime, timedelta

import requests
import streamlit as st
import extra_streamlit_components as stx

st.set_page_config(page_title="Login • TalentMatch Pro", page_icon="🔐", layout="wide")

FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY", "")

cookie_manager = stx.CookieManager()


def save_auth_cookies(email, id_token, refresh_token=""):
    expires_at = datetime.now() + timedelta(days=14)

    cookie_manager.set("tm_email", email or "", expires_at=expires_at)
    cookie_manager.set("tm_id_token", id_token or "", expires_at=expires_at)
    cookie_manager.set("tm_refresh_token", refresh_token or "", expires_at=expires_at)


def restore_auth_from_cookies():
    email = cookie_manager.get("tm_email")
    id_token = cookie_manager.get("tm_id_token")
    refresh_token = cookie_manager.get("tm_refresh_token")

    if email and id_token:
        st.session_state["user"] = {
            "email": email,
            "idToken": id_token,
            "id_token": id_token,
            "refreshToken": refresh_token or "",
            "refresh_token": refresh_token or "",
        }

        st.session_state["firebase_id_token"] = id_token
        st.session_state["id_token"] = id_token
        st.session_state["idToken"] = id_token
        st.session_state["token"] = id_token
        st.session_state["access_token"] = id_token
        st.session_state["refresh_token"] = refresh_token or ""


def clear_auth_state():
    for key in [
        "user",
        "profile",
        "firebase_id_token",
        "id_token",
        "idToken",
        "token",
        "access_token",
        "refresh_token",
        "checkout_url",
        "portal_url",
    ]:
        st.session_state.pop(key, None)

    cookie_manager.delete("tm_email")
    cookie_manager.delete("tm_id_token")
    cookie_manager.delete("tm_refresh_token")


def firebase_login(email, password):
    url = (
        "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
        f"?key={FIREBASE_API_KEY}"
    )

    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }

    return requests.post(url, json=payload, timeout=30)


restore_auth_from_cookies()

st.title("🔐 Login")
st.caption("Access your TalentMatch Pro account.")

current_user = st.session_state.get("user")

if isinstance(current_user, dict) and current_user.get("idToken"):
    st.success(f"Logged in as: {current_user.get('email', '')}")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Go to Pricing", use_container_width=True):
            st.switch_page("pages/pricing.py")

    with col2:
        if st.button("Logout", use_container_width=True):
            clear_auth_state()
            st.rerun()

    st.stop()

email = st.text_input("Email")
password = st.text_input("Password", type="password")

if st.button("Login", use_container_width=True):
    if not FIREBASE_API_KEY:
        st.error("FIREBASE_API_KEY is missing in Render Environment.")
        st.stop()

    if not email or not password:
        st.error("Enter email and password.")
        st.stop()

    response = firebase_login(email, password)

    if response.status_code != 200:
        st.error(response.text)
        st.stop()

    data = response.json()

    id_token = data.get("idToken", "")
    refresh_token = data.get("refreshToken", "")
    user_email = data.get("email", email)

    st.session_state["user"] = {
        "email": user_email,
        "idToken": id_token,
        "id_token": id_token,
        "refreshToken": refresh_token,
        "refresh_token": refresh_token,
        "localId": data.get("localId"),
        "local_id": data.get("localId"),
    }

    st.session_state["firebase_id_token"] = id_token
    st.session_state["id_token"] = id_token
    st.session_state["idToken"] = id_token
    st.session_state["token"] = id_token
    st.session_state["access_token"] = id_token
    st.session_state["refresh_token"] = refresh_token

    save_auth_cookies(user_email, id_token, refresh_token)

    st.success("Logged in successfully.")
    st.switch_page("pages/pricing.py")