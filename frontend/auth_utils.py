from __future__ import annotations

import os
import re
import time
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
FIREBASE_TOKEN_REFRESH_LEEWAY_SECONDS = 120
FIREBASE_TOKEN_REFRESH_TIMEOUT_SECONDS = 30


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
    return " ".join(part[:1].upper() + part[1:].lower() for part in parts[:3])


def _coerce_int(value: Any, default: int = 0) -> int:
    """Return a safe integer for backend usage values."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _profile_has_pro_access(profile: Mapping[str, Any]) -> bool:
    """Return Pro access from backend-authoritative profile fields."""
    plan = str(profile.get("plan") or "").strip().lower()
    subscription_status = str(
        profile.get("subscription_status") or ""
    ).strip().lower()
    paypal_status = str(
        profile.get("paypal_subscription_status") or ""
    ).strip().lower()

    return bool(
        profile.get("is_pro") is True
        or plan == "pro"
        or subscription_status in {"active", "approved"}
        or paypal_status in {"active", "approved"}
    )


def _profile_usage_by_type(profile: Mapping[str, Any]) -> dict[str, int]:
    """Normalize the backend usage breakdown for frontend session consumers."""
    raw_usage = profile.get("usage_by_type")
    if not isinstance(raw_usage, Mapping):
        raw_usage = {}

    legacy_cv_count = _coerce_int(
        profile.get("cv_analyses_used", profile.get("analyses_used", 0))
    )

    usage = {
        "cv_analysis": _coerce_int(
            raw_usage.get("cv_analysis"),
            legacy_cv_count,
        ),
        "ats_checker": _coerce_int(raw_usage.get("ats_checker")),
        "cv_rewrite": _coerce_int(raw_usage.get("cv_rewrite")),
        "semantic_match": _coerce_int(raw_usage.get("semantic_match")),
        "recruiter_mode": _coerce_int(raw_usage.get("recruiter_mode")),
    }

    for key, value in raw_usage.items():
        normalized_key = str(key or "").strip().lower()
        if normalized_key and normalized_key not in usage:
            usage[normalized_key] = _coerce_int(value)

    return usage


def _sync_profile_to_session(profile: Mapping[str, Any]) -> None:
    """Synchronize the backend-validated profile into Streamlit session state."""
    if not isinstance(profile, Mapping):
        return

    email = str(profile.get("email") or "").strip()
    full_name = _clean_display_name(
        profile.get("full_name") or profile.get("display_name") or profile.get("name")
    )
    is_admin = profile.get("is_admin") is True
    backend_plan = str(profile.get("plan") or "free").strip().lower() or "free"
    is_pro = _profile_has_pro_access(profile)
    plan = "pro" if is_pro else backend_plan
    usage_by_type = _profile_usage_by_type(profile)

    cv_analyses_used = _coerce_int(
        profile.get("cv_analyses_used", profile.get("analyses_used", 0))
    )
    analyses_used = _coerce_int(profile.get("analyses_used", cv_analyses_used))
    total_analyses = _coerce_int(
        profile.get("total_analyses", sum(usage_by_type.values()))
    )
    free_limit = _coerce_int(profile.get("free_limit"), 3)

    remaining_raw = profile.get("remaining")
    remaining = None if remaining_raw is None else _coerce_int(remaining_raw)
    upgrade_required = profile.get("upgrade_required") is True

    if is_pro:
        remaining = None
        upgrade_required = False

    usage_period = str(profile.get("usage_period") or "lifetime").strip().lower()

    st.session_state["is_admin"] = is_admin
    st.session_state["plan"] = plan
    st.session_state["is_pro"] = is_pro
    st.session_state["analyses_used"] = analyses_used
    st.session_state["cv_analyses_used"] = cv_analyses_used
    st.session_state["total_analyses"] = total_analyses
    st.session_state["usage_by_type"] = usage_by_type
    st.session_state["usage_period"] = usage_period
    st.session_state["free_limit"] = free_limit
    st.session_state["remaining"] = remaining
    st.session_state["upgrade_required"] = upgrade_required

    user_id = profile.get("id")
    if user_id is not None:
        st.session_state["user_id"] = user_id

    for key in (
        "paypal_customer_id",
        "paypal_subscription_id",
        "paypal_subscription_status",
        "subscription_status",
        "created_at",
    ):
        if key in profile:
            st.session_state[key] = profile.get(key)

    st.session_state["usage_cv_analysis"] = usage_by_type["cv_analysis"]
    st.session_state["usage_ats_checker"] = usage_by_type["ats_checker"]
    st.session_state["usage_cv_rewrite"] = usage_by_type["cv_rewrite"]
    st.session_state["usage_semantic_match"] = usage_by_type["semantic_match"]
    st.session_state["usage_recruiter_mode"] = usage_by_type["recruiter_mode"]

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

    if user_id is not None:
        user_state["id"] = user_id
    if email:
        user_state["email"] = email
    if full_name:
        user_state["full_name"] = full_name
        user_state["display_name"] = full_name
        user_state["name"] = full_name

    user_state.update(
        {
            "is_admin": is_admin,
            "plan": plan,
            "is_pro": is_pro,
            "analyses_used": analyses_used,
            "cv_analyses_used": cv_analyses_used,
            "total_analyses": total_analyses,
            "usage_by_type": usage_by_type,
            "usage_period": usage_period,
            "free_limit": free_limit,
            "remaining": remaining,
            "upgrade_required": upgrade_required,
        }
    )

    for key in (
        "paypal_customer_id",
        "paypal_subscription_id",
        "paypal_subscription_status",
        "subscription_status",
        "created_at",
    ):
        if key in profile:
            user_state[key] = profile.get(key)

    st.session_state["user"] = user_state


def save_auth(
    token: str,
    email: str = "",
    full_name: str = "",
    refresh_token: str = "",
    expires_in: Any = None,
) -> None:
    """
    Save authentication data in Streamlit session state.

    Multiple keys are stored for compatibility across old and new frontend pages.
    """
    for key in (
        "profile",
        "user_id",
        "plan",
        "is_pro",
        "paypal_customer_id",
        "paypal_subscription_id",
        "paypal_subscription_status",
        "subscription_status",
        "created_at",
        "analyses_used",
        "cv_analyses_used",
        "total_analyses",
        "usage_by_type",
        "usage_period",
        "free_limit",
        "remaining",
        "upgrade_required",
        "usage_cv_analysis",
        "usage_ats_checker",
        "usage_cv_rewrite",
        "usage_semantic_match",
        "usage_recruiter_mode",
        "profile_last_refresh_at",
        "profile_last_refresh_status",
        "profile_last_refresh_error",
        "profile_using_stale_cache",
        "refresh_token",
        "token_expires_at",
        "token_last_refresh_at",
        "token_refresh_status",
        "token_refresh_error",
    ):
        st.session_state.pop(key, None)

    clean_email = str(email or "").strip().lower()
    clean_name = _clean_display_name(full_name)

    st.session_state["token"] = token
    st.session_state["id_token"] = token

    clean_refresh_token = str(refresh_token or "").strip()
    if clean_refresh_token:
        st.session_state["refresh_token"] = clean_refresh_token

    expires_in_seconds = _coerce_int(expires_in)
    if expires_in_seconds > 0:
        st.session_state["token_expires_at"] = time.time() + expires_in_seconds

    st.session_state["token_refresh_status"] = "current"
    st.session_state["token_refresh_error"] = ""

    st.session_state["email"] = clean_email
    st.session_state["user_email"] = clean_email

    if clean_name:
        st.session_state["full_name"] = clean_name
        st.session_state["display_name"] = clean_name
        st.session_state["name"] = clean_name

    st.session_state["authenticated"] = True
    st.session_state["is_admin"] = False

    user_state: dict[str, Any] = {
        "email": clean_email,
        "is_admin": False,
    }
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
    """Remove authentication, profile, entitlement and usage state."""
    keys = [
        "token",
        "id_token",
        "email",
        "user_email",
        "authenticated",
        "is_admin",
        "profile",
        "user",
        "user_id",
        "full_name",
        "display_name",
        "name",
        "plan",
        "is_pro",
        "paypal_customer_id",
        "paypal_subscription_id",
        "paypal_subscription_status",
        "subscription_status",
        "created_at",
        "analyses_used",
        "cv_analyses_used",
        "total_analyses",
        "usage_by_type",
        "usage_period",
        "free_limit",
        "remaining",
        "upgrade_required",
        "usage_cv_analysis",
        "usage_ats_checker",
        "usage_cv_rewrite",
        "usage_semantic_match",
        "usage_recruiter_mode",
        "profile_last_refresh_at",
        "profile_last_refresh_status",
        "profile_last_refresh_error",
        "profile_using_stale_cache",
        "refresh_token",
        "token_expires_at",
        "token_last_refresh_at",
        "token_refresh_status",
        "token_refresh_error",
    ]

    for key in keys:
        st.session_state.pop(key, None)


def _raw_token() -> str:
    """Return the stored Firebase ID token without triggering a refresh."""
    return str(st.session_state.get("token") or st.session_state.get("id_token") or "")


def _firebase_refresh_error(response: requests.Response) -> str:
    """Return a bounded Firebase refresh error without exposing credentials."""
    try:
        payload = response.json()
    except Exception:
        payload = None

    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()[:200]

        if isinstance(error, str) and error.strip():
            return error.strip()[:200]

    return f"Firebase token refresh failed with HTTP {response.status_code}."


def _mark_auth_expired(message: str) -> None:
    """Fail closed when an authenticated session can no longer be renewed."""
    clean_message = str(message or "Authentication session expired.").strip()[:500]
    clear_auth()
    st.session_state["authenticated"] = False
    st.session_state["token_refresh_status"] = "reauthentication_required"
    st.session_state["token_refresh_error"] = clean_message


def refresh_firebase_token() -> bool:
    """Exchange the stored Firebase refresh token for a fresh ID token."""
    refresh_token = str(st.session_state.get("refresh_token") or "").strip()

    if not FIREBASE_API_KEY or not refresh_token:
        st.session_state["token_refresh_status"] = "unavailable"
        st.session_state["token_refresh_error"] = (
            "The session cannot be renewed. Please sign in again."
        )
        return False

    url = f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    try:
        response = requests.post(
            url,
            data=payload,
            timeout=FIREBASE_TOKEN_REFRESH_TIMEOUT_SECONDS,
        )
    except requests.RequestException:
        st.session_state["token_refresh_status"] = "temporarily_unavailable"
        st.session_state["token_refresh_error"] = (
            "Firebase session renewal is temporarily unavailable."
        )
        return False

    if response.status_code != 200:
        st.session_state["token_refresh_status"] = f"http_{response.status_code}"
        st.session_state["token_refresh_error"] = _firebase_refresh_error(response)
        return False

    try:
        data = response.json()
    except Exception:
        st.session_state["token_refresh_status"] = "invalid_json"
        st.session_state["token_refresh_error"] = (
            "Firebase returned an invalid session renewal response."
        )
        return False

    if not isinstance(data, dict):
        st.session_state["token_refresh_status"] = "invalid_response"
        st.session_state["token_refresh_error"] = (
            "Firebase returned an invalid session renewal response."
        )
        return False

    new_token = str(data.get("id_token") or "").strip()
    new_refresh_token = str(data.get("refresh_token") or refresh_token).strip()
    expires_in_seconds = _coerce_int(data.get("expires_in"))

    if not new_token or not new_refresh_token or expires_in_seconds <= 0:
        st.session_state["token_refresh_status"] = "incomplete_response"
        st.session_state["token_refresh_error"] = (
            "Firebase returned an incomplete session renewal response."
        )
        return False

    now = time.time()
    st.session_state["token"] = new_token
    st.session_state["id_token"] = new_token
    st.session_state["refresh_token"] = new_refresh_token
    st.session_state["token_expires_at"] = now + expires_in_seconds
    st.session_state["token_last_refresh_at"] = now
    st.session_state["token_refresh_status"] = "ok"
    st.session_state["token_refresh_error"] = ""
    st.session_state["authenticated"] = True
    return True


def _ensure_fresh_token() -> bool:
    """Refresh a near-expiry Firebase ID token and fail closed once expired."""
    token = _raw_token()
    if not token:
        return False

    try:
        expires_at = float(st.session_state.get("token_expires_at") or 0)
    except (TypeError, ValueError):
        expires_at = 0.0

    if expires_at <= 0:
        return True

    now = time.time()
    if now < expires_at - FIREBASE_TOKEN_REFRESH_LEEWAY_SECONDS:
        return True

    if refresh_firebase_token():
        return True

    if now < expires_at:
        return True

    _mark_auth_expired(
        st.session_state.get("token_refresh_error")
        or "Your authentication session expired. Please sign in again."
    )
    return False


def _recover_from_unauthorized() -> bool:
    """Attempt one forced token renewal after a backend 401 response."""
    if refresh_firebase_token():
        return True

    _mark_auth_expired(
        st.session_state.get("token_refresh_error")
        or "Your authentication session expired. Please sign in again."
    )
    return False


def restore_auth() -> bool:
    """Restore auth state from Streamlit session state."""
    token = _raw_token()

    if token and _ensure_fresh_token():
        current_token = _raw_token()
        st.session_state["token"] = current_token
        st.session_state["id_token"] = current_token
        st.session_state["authenticated"] = True

        cached_profile = _cached_profile()
        if cached_profile is not None:
            _sync_profile_to_session(cached_profile)

        return True

    st.session_state["authenticated"] = False
    return False


def get_token() -> str:
    """Return active auth token."""
    if not _ensure_fresh_token():
        return ""
    return _raw_token()


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
        response = requests.get(
            _build_url(endpoint),
            headers=get_auth_headers(),
            params=params,
            timeout=timeout,
        )

        if response.status_code == 401 and _raw_token():
            if _recover_from_unauthorized():
                response = requests.get(
                    _build_url(endpoint),
                    headers=get_auth_headers(),
                    params=params,
                    timeout=timeout,
                )
                if response.status_code == 401:
                    _mark_auth_expired(
                        "Your authentication session is no longer valid. "
                        "Please sign in again."
                    )

        return response
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

        response = requests.post(
            _build_url(endpoint),
            headers=get_auth_headers(),
            json=request_json if files is None else None,
            data=data,
            files=files,
            timeout=timeout,
        )

        if response.status_code == 401 and _raw_token():
            if _recover_from_unauthorized() and files is None:
                response = requests.post(
                    _build_url(endpoint),
                    headers=get_auth_headers(),
                    json=request_json,
                    data=data,
                    timeout=timeout,
                )
                if response.status_code == 401:
                    _mark_auth_expired(
                        "Your authentication session is no longer valid. "
                        "Please sign in again."
                    )

        return response
    except Exception as exc:
        return FakeResponse(500, str(exc))


# =========================
# Profile helpers
# =========================


def _cached_profile() -> dict[str, Any] | None:
    """Return the last successfully loaded profile without contacting the backend."""
    profile = st.session_state.get("profile")
    return profile if isinstance(profile, dict) and profile else None


def _response_error_message(response: requests.Response | FakeResponse) -> str:
    """Extract a bounded diagnostic message from an unsuccessful profile response."""
    try:
        payload = response.json()
    except Exception:
        payload = None

    if isinstance(payload, dict):
        detail = payload.get("detail")
        error = payload.get("error")

        if isinstance(detail, str) and detail.strip():
            return detail.strip()[:500]

        if isinstance(detail, dict):
            message = detail.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()[:500]

        if isinstance(error, str) and error.strip():
            return error.strip()[:500]

        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()[:500]

    return str(getattr(response, "text", "") or "Profile refresh failed.")[:500]


def refresh_profile() -> dict[str, Any] | None:
    """
    Reload the authenticated profile and preserve verified data on transient failures.

    A previously validated profile remains authoritative for the active Streamlit
    session when `/me` is temporarily unavailable, rate-limited, or returns a
    server-side error. Authentication failures invalidate the local session and
    require sign-in instead of silently presenting stale authenticated data.
    """
    cached_profile = _cached_profile()

    if not is_logged_in():
        st.session_state["profile_last_refresh_status"] = "not_authenticated"
        st.session_state["profile_using_stale_cache"] = bool(cached_profile)
        return cached_profile

    response = api_get("/me")
    status_code = int(getattr(response, "status_code", 500) or 500)

    if status_code != 200:
        st.session_state["profile_last_refresh_at"] = time.time()
        st.session_state["profile_last_refresh_status"] = f"http_{status_code}"
        st.session_state["profile_last_refresh_error"] = _response_error_message(
            response
        )

        if status_code in {401, 403}:
            if status_code == 403:
                _mark_auth_expired(
                    "Your authentication session is no longer authorized. "
                    "Please sign in again."
                )
            st.session_state["profile_using_stale_cache"] = False
            return None

        st.session_state["profile_using_stale_cache"] = bool(cached_profile)
        return cached_profile

    try:
        profile = response.json()
    except Exception:
        st.session_state["profile_last_refresh_at"] = time.time()
        st.session_state["profile_last_refresh_status"] = "invalid_json"
        st.session_state["profile_last_refresh_error"] = (
            "Backend returned an invalid profile response."
        )
        st.session_state["profile_using_stale_cache"] = bool(cached_profile)
        return cached_profile

    if not isinstance(profile, dict) or not profile:
        st.session_state["profile_last_refresh_at"] = time.time()
        st.session_state["profile_last_refresh_status"] = "invalid_profile"
        st.session_state["profile_last_refresh_error"] = (
            "Backend returned an empty or invalid profile."
        )
        st.session_state["profile_using_stale_cache"] = bool(cached_profile)
        return cached_profile

    st.session_state["profile"] = profile
    st.session_state["profile_last_refresh_at"] = time.time()
    st.session_state["profile_last_refresh_status"] = "ok"
    st.session_state["profile_last_refresh_error"] = ""
    st.session_state["profile_using_stale_cache"] = False
    _sync_profile_to_session(profile)
    return profile


def get_profile() -> dict[str, Any] | None:
    """Return the cached profile, loading it once when no cache exists."""
    cached_profile = _cached_profile()
    if cached_profile is not None:
        _sync_profile_to_session(cached_profile)
        return cached_profile

    return refresh_profile()


def load_profile() -> dict[str, Any] | None:
    """Compatibility alias for older imports."""
    return get_profile()


def is_pro_user() -> bool:
    """Check Pro access from the last successfully validated profile."""
    profile = get_profile()

    if not profile:
        return False

    return _profile_has_pro_access(profile)


def is_admin_user() -> bool:
    """
    Check administrator access from the last backend-validated profile.

    The frontend never derives administrator access from an email address or
    local session flag. The backend /me response is the authority and exposes
    only the boolean authorization decision.
    """
    profile = get_profile()

    if not profile:
        return False

    return profile.get("is_admin") is True


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
