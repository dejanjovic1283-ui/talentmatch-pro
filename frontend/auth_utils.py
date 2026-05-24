import os
import requests
import streamlit as st

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "https://talentmatch-backend-1283.onrender.com",
).rstrip("/")

FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY", "")


def save_auth(email: str, id_token: str, refresh_token: str = ""):
    st.session_state["logged_in"] = True
    st.session_state["user"] = {
        "email": email,
        "idToken": id_token,
        "id_token": id_token,
        "refreshToken": refresh_token,
        "refresh_token": refresh_token,
    }
    st.session_state["firebase_id_token"] = id_token
    st.session_state["id_token"] = id_token
    st.session_state["token"] = id_token
    st.session_state["refresh_token"] = refresh_token


def clear_auth():
    keys = [
        "logged_in",
        "user",
        "profile",
        "firebase_id_token",
        "id_token",
        "token",
        "refresh_token",
        "analysis_result",
        "ats_result",
        "history_items",
    ]
    for key in keys:
        st.session_state.pop(key, None)


def get_token():
    return (
        st.session_state.get("firebase_id_token")
        or st.session_state.get("id_token")
        or st.session_state.get("token")
        or ""
    )


def is_logged_in():
    return bool(get_token())


def get_auth_headers():
    token = get_token()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def api_get(path: str, timeout: int = 30):
    return requests.get(
        f"{BACKEND_URL}{path}",
        headers=get_auth_headers(),
        timeout=timeout,
    )


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
    except Exception:
        pass

    return None


def refresh_profile():
    st.session_state.pop("profile", None)
    return load_profile()


def get_profile():
    return st.session_state.get("profile") or load_profile() or {}


def is_pro_user():
    profile = get_profile()
    return bool(
        profile.get("is_pro")
        or profile.get("pro")
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