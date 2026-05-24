import os
import requests
import streamlit as st

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "https://talentmatch-backend-1283.onrender.com",
).rstrip("/")


def init_auth_state():
    defaults = {
        "auth_token": None,
        "user": None,
        "profile": None,
        "is_pro": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def set_auth(token: str, user: dict | None = None):
    init_auth_state()
    st.session_state["auth_token"] = token
    if user:
        st.session_state["user"] = user


def clear_auth():
    init_auth_state()
    st.session_state["auth_token"] = None
    st.session_state["user"] = None
    st.session_state["profile"] = None
    st.session_state["is_pro"] = False


def restore_auth():
    init_auth_state()
    return None


def get_token():
    init_auth_state()
    return st.session_state.get("auth_token")


def is_logged_in():
    return bool(get_token())


def get_auth_headers():
    token = get_token()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def api_get(path: str, timeout: int = 30):
    url = f"{BACKEND_URL}{path}"
    return requests.get(url, headers=get_auth_headers(), timeout=timeout)


def api_post(path: str, json=None, files=None, data=None, timeout: int = 60):
    url = f"{BACKEND_URL}{path}"
    return requests.post(
        url,
        headers=get_auth_headers(),
        json=json,
        files=files,
        data=data,
        timeout=timeout,
    )


def refresh_profile():
    init_auth_state()

    if not is_logged_in():
        return None

    try:
        response = api_get("/me")
        if response.status_code != 200:
            return None

        profile = response.json()
        st.session_state["profile"] = profile
        st.session_state["is_pro"] = bool(
            profile.get("is_pro") or profile.get("plan") == "pro"
        )
        return profile

    except Exception:
        return None


def get_profile():
    init_auth_state()
    if st.session_state.get("profile"):
        return st.session_state["profile"]
    return refresh_profile()


def is_pro_user():
    profile = get_profile()
    if not profile:
        return False
    return bool(profile.get("is_pro") or profile.get("plan") == "pro")