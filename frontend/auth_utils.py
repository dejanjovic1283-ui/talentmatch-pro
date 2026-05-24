import os
import requests
import streamlit as st


# =========================
# Safe config loader
# =========================

def get_config(key: str, default: str = "") -> str:
    """
    Read config safely.

    Priority:
    1. Render environment variables
    2. Streamlit secrets.toml
    3. Default value
    """
    value = os.getenv(key)
    if value:
        return value

    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


BACKEND_URL = get_config(
    "BACKEND_URL",
    "https://talentmatch-backend-1283.onrender.com"
)

FIREBASE_API_KEY = get_config("FIREBASE_API_KEY")


# =========================
# Session auth helpers
# =========================

def save_auth(token: str, email: str = "") -> None:
    """
    Save auth token and email in Streamlit session state.
    """
    st.session_state["token"] = token
    st.session_state["email"] = email


def clear_auth() -> None:
    """
    Clear all auth-related session data.
    """
    for key in ["token", "email", "profile"]:
        st.session_state.pop(key, None)


def restore_auth() -> bool:
    """
    Compatibility function for older files.
    Auth is stored in session state.
    """
    return bool(st.session_state.get("token"))


def get_token() -> str:
    """
    Return current auth token.
    """
    return st.session_state.get("token", "")


def is_logged_in() -> bool:
    """
    Check if user is logged in.
    """
    return bool(get_token())


def get_auth_headers() -> dict:
    """
    Return Authorization headers for backend requests.
    """
    token = get_token()

    if not token:
        return {}

    return {
        "Authorization": f"Bearer {token}"
    }


def get_headers() -> dict:
    """
    Compatibility alias used by older files.
    """
    return get_auth_headers()


# =========================
# Backend API helpers
# =========================

def api_get(endpoint: str, params=None, timeout: int = 60):
    """
    Safe GET request helper.
    Supports timeout parameter.
    """
    try:
        return requests.get(
            f"{BACKEND_URL}{endpoint}",
            headers=get_auth_headers(),
            params=params,
            timeout=timeout
        )
    except Exception as e:
        return FakeResponse(500, str(e))


def api_post(
    endpoint: str,
    payload=None,
    json=None,
    data=None,
    files=None,
    timeout: int = 120
):
    """
    Safe POST request helper.

    Supports:
    - json payloads
    - form data
    - file uploads
    - timeout parameter
    """
    try:
        request_json = json if json is not None else payload

        return requests.post(
            f"{BACKEND_URL}{endpoint}",
            headers=get_auth_headers(),
            json=request_json if files is None else None,
            data=data,
            files=files,
            timeout=timeout
        )
    except Exception as e:
        return FakeResponse(500, str(e))


class FakeResponse:
    """
    Fallback response object when request fails.
    """

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.text = message

    def json(self):
        return {
            "detail": self.text,
            "error": self.text
        }


# =========================
# Profile helpers
# =========================

def refresh_profile():
    """
    Reload user profile from backend.
    """
    if not is_logged_in():
        return None

    response = api_get("/me")

    if response.status_code != 200:
        return None

    try:
        profile = response.json()
        st.session_state["profile"] = profile
        return profile
    except Exception:
        return None


def get_profile():
    """
    Get cached profile or refresh it.
    """
    profile = st.session_state.get("profile")

    if profile:
        return profile

    return refresh_profile()


def load_profile():
    """
    Compatibility alias for older imports.
    """
    return get_profile()


def is_pro_user() -> bool:
    """
    Check if current user has Pro access.
    """
    profile = get_profile()

    if not profile:
        return False

    return bool(
        profile.get("is_pro")
        or profile.get("plan") == "pro"
        or profile.get("subscription_status") == "active"
    )


# =========================
# Firebase login
# =========================

def firebase_login(email: str, password: str):
    """
    Login with Firebase REST API.
    Returns tuple: (data, error_message)
    """
    if not FIREBASE_API_KEY:
        return None, "Missing FIREBASE_API_KEY"

    url = (
        "https://identitytoolkit.googleapis.com/"
        f"v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    )

    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }

    try:
        response = requests.post(url, json=payload, timeout=60)

        if response.status_code != 200:
            try:
                error_data = response.json()
                message = error_data.get("error", {}).get("message", response.text)
            except Exception:
                message = response.text

            return None, message

        return response.json(), None

    except Exception as e:
        return None, str(e)