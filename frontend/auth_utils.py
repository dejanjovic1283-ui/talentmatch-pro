import os
from datetime import datetime, timedelta

import requests
import streamlit as st
import extra_streamlit_components as stx

BACKEND_URL = os.getenv("BACKEND_URL", "https://talentmatch-backend-1283.onrender.com").rstrip("/")
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY", "")

cookie_manager = stx.CookieManager()


def get_cookie_snapshot():
    if "_tm_cookie_snapshot" not in st.session_state:
        st.session_state["_tm_cookie_snapshot"] = cookie_manager.get_all() or {}
    return st.session_state["_tm_cookie_snapshot"]


def save_auth(email: str, id_token: str, refresh_token: str = ""):
    expires_at = datetime.now() + timedelta(days=14)

    cookie_manager.set("tm_email", email or "", expires_at=expires_at)
    cookie_manager.set("tm_id_token", id_token or "", expires_at=expires_at)
    cookie_manager.set("tm_refresh_token", refresh_token or "", expires_at=expires_at)

    st.session_state["_tm_cookie_snapshot"] = {
        "tm_email": email or "",
        "tm_id_token": id_token or "",
        "tm_refresh_token": refresh_token or "",
    }

    st.session_state["user"] = {
        "email": email or "",
        "idToken": id_token or "",
        "id_token": id_token or "",
        "refreshToken": refresh_token or "",
        "refresh_token": refresh_token or "",
    }

    st.session_state["firebase_id_token"] = id_token
    st.session_state["id_token"] = id_token
    st.session_state["idToken"] = id_token
    st.session_state["token"] = id_token
    st.session_state["access_token"] = id_token
    st.session_state["refresh_token"] = refresh_token


def restore_auth():
    if st.session_state.get("firebase_id_token"):
        return

    cookies = get_cookie_snapshot()

    email = cookies.get("tm_email")
    token = cookies.get("tm_id_token")
    refresh_token = cookies.get("tm_refresh_token", "")

    if token:
        st.session_state["user"] = {
            "email": email or "",
            "idToken": token,
            "id_token": token,
            "refreshToken": refresh_token or "",
            "refresh_token": refresh_token or "",
        }

        st.session_state["firebase_id_token"] = token
        st.session_state["id_token"] = token
        st.session_state["idToken"] = token
        st.session_state["token"] = token
        st.session_state["access_token"] = token
        st.session_state["refresh_token"] = refresh_token or ""


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
        "checkout_url",
        "portal_url",
        "_tm_cookie_snapshot",
    ]:
        st.session_state.pop(key, None)

    cookie_manager.delete("tm_email")
    cookie_manager.delete("tm_id_token")
    cookie_manager.delete("tm_refresh_token")


def get_token():
    restore_auth()

    return (
        st.session_state.get("firebase_id_token")
        or st.session_state.get("id_token")
        or st.session_state.get("idToken")
        or st.session_state.get("token")
        or st.session_state.get("access_token")
        or ""
    )


def get_auth_headers():
    token = get_token()
    return {"Authorization": f"Bearer {token}"} if token else {}


def is_logged_in():
    return bool(get_token())


def api_get(path: str, timeout: int = 30):
    return requests.get(f"{BACKEND_URL}{path}", headers=get_auth_headers(), timeout=timeout)


def api_post(path: str, data=None, json_data=None, files=None, timeout: int = 120):
    return requests.post(
        f"{BACKEND_URL}{path}",
        headers=get_auth_headers(),
        data=data,
        json=json_data,
        files=files,
        timeout=timeout,
    )


def load_profile():
    if not is_logged_in():
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


def is_pro_user():
    profile = get_profile()

    return bool(
        profile.get("is_pro")
        or profile.get("plan") == "pro"
        or profile.get("subscription_status") in ["active", "trialing"]
    )


def firebase_login(email: str, password: str):
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