import os
from typing import Any, Optional

import requests
import streamlit as st


# =========================
# Safe config loader
# =========================

def get_config(key: str, default: str = "") -> str:
    """
    Read configuration safely.

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
).rstrip("/")

FIREBASE_API_KEY = get_config("FIREBASE_API_KEY")


# =========================
# Fake response helper
# =========================

class FakeResponse:
    """
    Small response-like object used when a request fails before reaching the server.
    """

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.text = message

    def json(self) -> dict:
        return {
            "detail": self.text,
            "error": self.text,
        }


# =========================
# Session auth helpers
# =========================


def _clean_display_name(value: Any) -> str:
    """Return a clean display name like 'Dejan Jovic' from profile/Firebase values."""
    raw = str(value or "").strip()
    if not raw:
        return ""

    if "@" in raw:
        raw = raw.split("@", 1)[0]

    raw = raw.replace(".", " ").replace("_", " ").replace("-", " ")
    raw = __import__("re").sub(r"[0-9]+", "", raw)
    raw = __import__("re").sub(r"(?<=[a-z])(?=[A-Z])", " ", raw)
    raw = __import__("re").sub(r"\s+", " ", raw).strip()

    if not raw:
        return ""

    parts = [part for part in raw.split() if part]
    display_name = " ".join(part[:1].upper() + part[1:].lower() for part in parts[:3])
    compact = __import__("re").sub(r"[^a-zA-Z]", "", display_name).lower()
    if "dejan" in compact and "jovic" in compact:
        return "Dejan Jovic"
    return display_name


def _sync_profile_to_session(profile: dict) -> None:
    """Keep profile identity fields available for all frontend pages."""
    if not isinstance(profile, dict):
        return

    email = str(profile.get("email") or "").strip()
    full_name = _clean_display_name(
        profile.get("full_name") or profile.get("display_name") or profile.get("name")
    )

    if email:
        st.session_state["email"] = email
        st.session_state["user_email"] = email

    if full_name:
        st.session_state["full_name"] = full_name
        st.session_state["display_name"] = full_name
        st.session_state["name"] = full_name

    user_state = st.session_state.get("user")
    if not isinstance(user_state, dict):
        user_state = {}

    if email:
        user_state["email"] = email
    if full_name:
        user_state["full_name"] = full_name
        user_state["display_name"] = full_name
        user_state["name"] = full_name

    st.session_state["user"] = user_state

def save_auth(token: str, email: str = "", full_name: str = "") -> None:
    """
    Save authentication data in Streamlit session state.

    Multiple keys are stored for compatibility across old and new frontend pages.
    """
    clean_email = str(email or "").strip().lower()
    clean_name = _clean_display_name(full_name)

    st.session_state["token"] = token
    st.session_state["id_token"] = token

    st.session_state["email"] = clean_email
    st.session_state["user_email"] = clean_email

    if clean_name:
        st.session_state["full_name"] = clean_name
        st.session_state["display_name"] = clean_name
        st.session_state["name"] = clean_name

    st.session_state["authenticated"] = True

    user_state = {"email": clean_email}
    if clean_name:
        user_state.update(
            {
                "full_name": clean_name,
                "display_name": clean_name,
                "name": clean_name,
            }
        )
    st.session_state["user"] = user_state


def clear_auth() -> None:
    """
    Remove authentication state.
    """
    keys = [
        "token",
        "id_token",
        "email",
        "user_email",
        "authenticated",
        "profile",
        "user",
        "full_name",
        "display_name",
        "name",
    ]

    for key in keys:
        st.session_state.pop(key, None)


def restore_auth() -> bool:
    """
    Restore auth state from Streamlit session state.
    """
    token = (
        st.session_state.get("token")
        or st.session_state.get("id_token")
    )

    if token:
        st.session_state["token"] = token
        st.session_state["id_token"] = token
        st.session_state["authenticated"] = True
        return True

    st.session_state["authenticated"] = False
    return False


def get_token() -> str:
    """
    Return active auth token.
    """
    return (
        st.session_state.get("token")
        or st.session_state.get("id_token")
        or ""
    )


def is_logged_in() -> bool:
    """
    Check whether user is logged in.
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
        "Authorization": f"Bearer {token}",
    }


def get_headers() -> dict:
    """
    Compatibility alias used by older files.
    """
    return get_auth_headers()


# =========================
# Backend API helpers
# =========================

def api_get(endpoint: str, params: Optional[dict] = None, timeout: int = 60):
    """
    Safe GET request helper.
    """
    try:
        return requests.get(
            f"{BACKEND_URL}{endpoint}",
            headers=get_auth_headers(),
            params=params,
            timeout=timeout,
        )
    except Exception as e:
        return FakeResponse(500, str(e))


def api_post(
    endpoint: str,
    payload: Optional[dict] = None,
    json: Optional[dict] = None,
    data: Optional[dict] = None,
    files: Optional[dict] = None,
    timeout: int = 120,
):
    """
    Safe POST request helper.

    Supports JSON payloads, form data, file uploads, and timeout.
    """
    try:
        request_json = json if json is not None else payload

        return requests.post(
            f"{BACKEND_URL}{endpoint}",
            headers=get_auth_headers(),
            json=request_json if files is None else None,
            data=data,
            files=files,
            timeout=timeout,
        )
    except Exception as e:
        return FakeResponse(500, str(e))


# =========================
# Profile helpers
# =========================

def refresh_profile() -> Optional[dict]:
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
        if isinstance(profile, dict):
            _sync_profile_to_session(profile)
        return profile
    except Exception:
        return None


def get_profile() -> Optional[dict]:
    """
    Get cached profile or refresh it.
    """
    profile = st.session_state.get("profile")

    if profile:
        return profile

    return refresh_profile()


def load_profile() -> Optional[dict]:
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

def firebase_login(email: str, password: str) -> tuple[Optional[dict], Optional[str]]:
    """
    Login with Firebase REST API.

    Returns:
    - data dict on success
    - error message on failure
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
        "returnSecureToken": True,
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=60,
        )

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