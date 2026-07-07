from __future__ import annotations

import os
import re
from typing import IO, Any, Mapping, Optional, Sequence, TypeAlias

import requests
import streamlit as st


# =========================
# Type aliases
# =========================

Headers: TypeAlias = dict[str, str]
QueryParams: TypeAlias = Mapping[str, Any]
JsonPayload: TypeAlias = Mapping[str, Any]
FormData: TypeAlias = Mapping[str, Any]

FileTuple: TypeAlias = (
    tuple[str, bytes, str]
    | tuple[str, bytes, str, Mapping[str, str]]
    | tuple[str, IO[Any], str]
    | tuple[str, IO[Any], str, Mapping[str, str]]
)
FileValue: TypeAlias = bytes | IO[Any] | FileTuple
RequestFiles: TypeAlias = Mapping[str, FileValue] | Sequence[tuple[str, FileValue]]


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
        secret_value = st.secrets.get(key, default)
        return str(secret_value or default)
    except Exception:
        return default


BACKEND_URL = get_config(
    "BACKEND_URL",
    "https://api.talentmatchcv.com",
).rstrip("/")

FIREBASE_API_KEY = get_config("FIREBASE_API_KEY")


# =========================
# Fake response helper
# =========================

class FakeResponse:
    """
    Small response-like object used when a request fails before reaching the server.

    It intentionally exposes the same minimal attributes/methods used across the
    frontend pages: status_code, text, headers and json().
    """

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.text = message
        self.headers: Headers = {"content-type": "application/json"}

    def json(self) -> dict[str, str]:
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
    raw = re.sub(r"[0-9]+", "", raw)
    raw = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()

    if not raw:
        return ""

    parts = [part for part in raw.split() if part]
    display_name = " ".join(part[:1].upper() + part[1:].lower() for part in parts[:3])
    compact = re.sub(r"[^a-zA-Z]", "", display_name).lower()

    if "dejan" in compact and "jovic" in compact:
        return "Dejan Jovic"

    return display_name


def _sync_profile_to_session(profile: Mapping[str, Any]) -> None:
    """Keep profile identity fields available for all frontend pages."""
    if not isinstance(profile, Mapping):
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

    user_state: dict[str, str] = {"email": clean_email}
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
    """Remove authentication state."""
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
    """Restore auth state from Streamlit session state."""
    token = st.session_state.get("token") or st.session_state.get("id_token")

    if token:
        st.session_state["token"] = token
        st.session_state["id_token"] = token
        st.session_state["authenticated"] = True
        return True

    st.session_state["authenticated"] = False
    return False


def get_token() -> str:
    """Return active auth token."""
    return str(st.session_state.get("token") or st.session_state.get("id_token") or "")


def is_logged_in() -> bool:
    """Check whether user is logged in."""
    return bool(get_token())


def get_auth_headers() -> Headers:
    """Return Authorization headers for backend requests."""
    token = get_token()

    if not token:
        return {}

    return {"Authorization": f"Bearer {token}"}


def get_headers() -> Headers:
    """Compatibility alias used by older files."""
    return get_auth_headers()


# =========================
# Backend API helpers
# =========================


def _build_url(endpoint: str) -> str:
    """Build a backend URL from either '/path' or 'path'."""
    clean_endpoint = str(endpoint or "").strip()
    if not clean_endpoint:
        clean_endpoint = "/"
    if not clean_endpoint.startswith("/"):
        clean_endpoint = f"/{clean_endpoint}"
    return f"{BACKEND_URL}{clean_endpoint}"


def api_get(
    endpoint: str,
    params: QueryParams | None = None,
    timeout: int = 60,
) -> requests.Response | FakeResponse:
    """Safe GET request helper."""
    try:
        return requests.get(
            _build_url(endpoint),
            headers=get_auth_headers(),
            params=params,
            timeout=timeout,
        )
    except Exception as exc:
        return FakeResponse(500, str(exc))


def api_post(
    endpoint: str,
    payload: JsonPayload | None = None,
    json: JsonPayload | None = None,
    data: FormData | None = None,
    files: RequestFiles | None = None,
    timeout: int = 120,
) -> requests.Response | FakeResponse:
    """
    Safe POST request helper.

    Supports:
    - JSON payloads: api_post('/endpoint', payload={...}) or api_post('/endpoint', json={...})
    - Form data: api_post('/endpoint', data={...})
    - Single file upload for ATS/CV/Semantic pages:
        files={'file': ('cv.pdf', b'...', 'application/pdf')}
    - Multiple files under the same field for Recruiter Mode:
        files=[('files', ('a.pdf', b'...', 'application/pdf')), ...]

    The files type is intentionally compatible with requests.post(), so Pylance
    accepts both dictionary and list-of-tuples upload formats.
    """
    try:
        request_json = json if json is not None else payload

        return requests.post(
            _build_url(endpoint),
            headers=get_auth_headers(),
            json=request_json if files is None else None,
            data=data,
            files=files,
            timeout=timeout,
        )
    except Exception as exc:
        return FakeResponse(500, str(exc))


# =========================
# Profile helpers
# =========================


def refresh_profile() -> dict[str, Any] | None:
    """Reload user profile from backend."""
    if not is_logged_in():
        return None

    response = api_get("/me")

    if response.status_code != 200:
        return None

    try:
        profile = response.json()
    except Exception:
        return None

    if not isinstance(profile, dict):
        return None

    st.session_state["profile"] = profile
    _sync_profile_to_session(profile)
    return profile


def get_profile() -> dict[str, Any] | None:
    """Get cached profile or refresh it."""
    profile = st.session_state.get("profile")

    if isinstance(profile, dict):
        return profile

    return refresh_profile()


def load_profile() -> dict[str, Any] | None:
    """Compatibility alias for older imports."""
    return get_profile()


def is_pro_user() -> bool:
    """Check if current user has Pro access."""
    profile = get_profile()

    if not profile:
        return False

    subscription_status = str(profile.get("subscription_status") or "").lower()
    paypal_status = str(profile.get("paypal_subscription_status") or "").lower()
    plan = str(profile.get("plan") or "").lower()

    return bool(
        profile.get("is_pro")
        or plan == "pro"
        or subscription_status in {"active", "approved"}
        or paypal_status in {"active", "approved"}
    )


# =========================
# Firebase login
# =========================


def firebase_login(email: str, password: str) -> tuple[dict[str, Any] | None, str | None]:
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

            return None, str(message)

        firebase_payload = response.json()
        if not isinstance(firebase_payload, dict):
            return None, "Firebase returned invalid response."

        return firebase_payload, None

    except Exception as exc:
        return None, str(exc)
