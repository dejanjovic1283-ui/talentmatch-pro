from __future__ import annotations

import json
import os
import re
import time
from html import escape as html_escape
from typing import IO, Any, Mapping, Optional, Sequence, TypeAlias

import requests
import streamlit as st
import streamlit.components.v1 as components


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
PERSISTENT_SESSION_HEADER = "X-TalentMatch-Session"
PERSISTENT_SESSION_COOKIE_NAME = get_config("AUTH_SESSION_COOKIE_NAME", "tm_session")
PERSISTENT_SESSION_RESTORE_TIMEOUT_SECONDS = 35
PERSISTENT_SESSION_BOOTSTRAP_TIMEOUT_SECONDS = 35
FIREBASE_TOKEN_REFRESH_LEEWAY_SECONDS = 120
FIREBASE_TOKEN_REFRESH_TIMEOUT_SECONDS = 30
PROFILE_REQUEST_TIMEOUT_SECONDS = 60
PROFILE_REFRESH_COOLDOWN_SECONDS = 5
PROFILE_RETRY_DELAY_SECONDS = 0.35
BACKEND_READINESS_TIMEOUT_SECONDS = 12
BACKEND_READINESS_CACHE_SECONDS = 20

PROFILE_STATE_NOT_LOADED = "not_loaded"
PROFILE_STATE_LOADING = "loading"
PROFILE_STATE_VERIFIED = "verified"
PROFILE_STATE_STALE = "stale"
PROFILE_STATE_UNAVAILABLE = "unavailable"
PROFILE_STATE_REAUTHENTICATION_REQUIRED = "reauthentication_required"
PROFILE_STATE_NOT_AUTHENTICATED = "not_authenticated"

TRANSIENT_PROFILE_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})


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
    # New `/me` responses always include ``is_pro``.  When that explicit
    # decision is present it is the only entitlement signal we trust; a stale
    # PayPal status or a client-crafted ``plan`` value must never grant access.
    if "is_pro" in profile:
        return profile.get("is_pro") is True

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
    *,
    persistent: bool = False,
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
        "profile_availability",
        "profile_last_attempt_at",
        "profile_last_verified_at",
        "backend_readiness",
        "backend_readiness_status",
        "backend_readiness_error",
        "backend_readiness_checked_at",
        "refresh_token",
        "token_expires_at",
        "token_last_refresh_at",
        "token_refresh_status",
        "token_refresh_error",
        "auth_mode",
        "persistent_session_status",
        "persistent_session_error",
        "persistent_session_activation_url",
        "persistent_session_restored_at",
        "persistent_session_restore_last_attempt_at",
        "persistent_session_revoke_attempted",
    ):
        st.session_state.pop(key, None)

    clean_email = str(email or "").strip().lower()
    clean_name = _clean_display_name(full_name)

    st.session_state["token"] = token
    st.session_state["id_token"] = token

    clean_refresh_token = str(refresh_token or "").strip()
    if clean_refresh_token and not persistent:
        st.session_state["refresh_token"] = clean_refresh_token

    expires_in_seconds = _coerce_int(expires_in)
    if expires_in_seconds > 0:
        st.session_state["token_expires_at"] = time.time() + expires_in_seconds

    st.session_state["token_refresh_status"] = "current"
    st.session_state["token_refresh_error"] = ""
    st.session_state["profile_availability"] = PROFILE_STATE_NOT_LOADED
    st.session_state["auth_mode"] = "persistent" if persistent else "firebase"
    if persistent:
        st.session_state["persistent_session_status"] = "restored"
        st.session_state["persistent_session_error"] = ""
        st.session_state["persistent_session_restored_at"] = time.time()

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


def clear_auth(*, revoke_persistent_session: bool = True) -> None:
    """Remove authentication, profile, entitlement and usage state."""
    if revoke_persistent_session:
        _revoke_persistent_session_silently()

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
        "profile_availability",
        "profile_last_attempt_at",
        "profile_last_verified_at",
        "backend_readiness",
        "backend_readiness_status",
        "backend_readiness_error",
        "backend_readiness_checked_at",
        "refresh_token",
        "token_expires_at",
        "token_last_refresh_at",
        "token_refresh_status",
        "token_refresh_error",
        "auth_mode",
        "persistent_session_status",
        "persistent_session_error",
        "persistent_session_activation_url",
        "persistent_session_restored_at",
        "persistent_session_restore_last_attempt_at",
        "persistent_session_revoke_attempted",
    ]

    for key in keys:
        st.session_state.pop(key, None)


def logout_and_redirect() -> None:
    """Clear local state, revoke server state, and delete the browser cookie.

    Streamlit's backend-to-backend ``requests.post`` call cannot forward a
    ``Set-Cookie`` response to the user's browser.  The browser must therefore
    navigate directly to the API logout endpoint, which revokes the session
    from the browser cookie and returns a matching expired cookie.
    """
    clear_auth()
    logout_url = _build_url("/auth/session/logout")
    script_url = json.dumps(logout_url)
    link_url = html_escape(logout_url, quote=True)

    components.html(
        f"""
        <script>
        (() => {{
            const target = {script_url};
            try {{
                window.top.location.replace(target);
            }} catch (error) {{
                window.parent.location.replace(target);
            }}
        }})();
        </script>
        <a href="{link_url}" target="_top" rel="noreferrer">Continue securely</a>
        """,
        height=1,
        scrolling=False,
    )
    st.stop()


def _raw_token() -> str:
    """Return the stored Firebase ID token without triggering a refresh."""
    return str(st.session_state.get("token") or st.session_state.get("id_token") or "")


def _persistent_session_cookie() -> str:
    """Read the opaque HttpOnly cookie exposed to Streamlit's server context."""
    try:
        cookies = st.context.cookies
        raw_cookie = cookies.get(PERSISTENT_SESSION_COOKIE_NAME, "")
    except Exception:
        return ""

    cookie = str(raw_cookie or "").strip()
    return cookie if 20 <= len(cookie) <= 512 else ""


def _persistent_session_headers() -> Headers:
    """Return the internal server-to-server header for the opaque cookie value."""
    cookie = _persistent_session_cookie()
    return {PERSISTENT_SESSION_HEADER: cookie} if cookie else {}


def _set_persistent_session_error(status: str, message: str) -> None:
    st.session_state["persistent_session_status"] = status
    st.session_state["persistent_session_error"] = str(message or "").strip()[:500]
    st.session_state["persistent_session_restore_last_attempt_at"] = time.time()


def _restore_persistent_session() -> bool:
    """Restore a fresh Firebase ID token from the backend-held encrypted token."""
    headers = _persistent_session_headers()
    if not headers:
        return False

    try:
        last_attempt_at = float(
            st.session_state.get("persistent_session_restore_last_attempt_at") or 0
        )
    except (TypeError, ValueError):
        last_attempt_at = 0.0

    if time.time() - last_attempt_at < 5:
        return False

    try:
        response = requests.post(
            _build_url("/auth/session/restore"),
            headers=headers,
            timeout=PERSISTENT_SESSION_RESTORE_TIMEOUT_SECONDS,
        )
    except requests.RequestException:
        _set_persistent_session_error(
            "temporarily_unavailable",
            "Secure session restoration is temporarily unavailable.",
        )
        return False

    if response.status_code != 200:
        if response.status_code in {401, 403}:
            _set_persistent_session_error(
                "reauthentication_required",
                "Your secure session has expired. Please sign in again.",
            )
        else:
            _set_persistent_session_error(
                "temporarily_unavailable",
                _response_error_message(response),
            )
        return False

    try:
        payload = response.json()
    except (TypeError, ValueError):
        payload = None

    if not isinstance(payload, Mapping):
        _set_persistent_session_error(
            "invalid_response",
            "The secure-session service returned an invalid response.",
        )
        return False

    token = str(payload.get("id_token") or "").strip()
    email = str(payload.get("email") or "").strip()
    full_name = str(payload.get("full_name") or "").strip()
    expires_in = _coerce_int(payload.get("expires_in"))

    if not token or expires_in <= 0:
        _set_persistent_session_error(
            "invalid_response",
            "The secure-session service returned incomplete credentials.",
        )
        return False

    save_auth(
        token=token,
        email=email,
        full_name=full_name,
        expires_in=expires_in,
        persistent=True,
    )
    return True


def _revoke_persistent_session_silently() -> None:
    """Invalidate the server-side session while keeping logout safe on failure."""
    headers = _persistent_session_headers()
    if not headers:
        return

    try:
        requests.post(
            _build_url("/auth/session/revoke"),
            headers=headers,
            timeout=PERSISTENT_SESSION_RESTORE_TIMEOUT_SECONDS,
        )
    except requests.RequestException:
        # The local auth state is still cleared. The opaque server record will
        # expire naturally if the backend cannot be reached at logout time.
        pass


def begin_persistent_session() -> tuple[str | None, str | None]:
    """
    Store a verified Firebase refresh token only on the backend.

    The returned URL contains a short-lived, single-use activation code. The
    next browser navigation receives an HttpOnly cookie; it never receives the
    Firebase refresh token.
    """
    refresh_token = str(st.session_state.get("refresh_token") or "").strip()
    token = get_token()

    if not token or not refresh_token:
        return None, "Your sign-in session is incomplete. Please try again."

    try:
        response = requests.post(
            _build_url("/auth/session/bootstrap"),
            headers={"Authorization": f"Bearer {token}"},
            json={"refresh_token": refresh_token},
            timeout=PERSISTENT_SESSION_BOOTSTRAP_TIMEOUT_SECONDS,
        )
    except requests.RequestException:
        return None, "Secure session setup is temporarily unavailable. Please try again."

    if response.status_code != 201:
        return None, _response_error_message(response)

    try:
        payload = response.json()
    except (TypeError, ValueError):
        payload = None

    if not isinstance(payload, Mapping):
        return None, "Secure session setup returned an invalid response."

    activation_url = str(payload.get("activation_url") or "").strip()
    if not activation_url.startswith(("https://", "http://")):
        return None, "Secure session setup returned an invalid activation link."

    # The backend has stored an encrypted replacement. Do not keep the raw
    # Firebase refresh token in this Streamlit session any longer than needed.
    st.session_state.pop("refresh_token", None)
    st.session_state["auth_mode"] = "persistent_pending_activation"
    st.session_state["persistent_session_status"] = "activation_pending"
    st.session_state["persistent_session_error"] = ""
    st.session_state["persistent_session_activation_url"] = activation_url
    return activation_url, None


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
    # A transient backend outage must not revoke a server-side session simply
    # because the current Firebase ID token reached its one-hour expiry.
    clear_auth(revoke_persistent_session=False)
    st.session_state["authenticated"] = False
    st.session_state["token_refresh_status"] = "reauthentication_required"
    st.session_state["token_refresh_error"] = clean_message


def refresh_firebase_token() -> bool:
    """Renew an ID token from the durable session or legacy in-memory token."""
    auth_mode = str(st.session_state.get("auth_mode") or "").strip().lower()
    if auth_mode == "persistent" or (
        not st.session_state.get("refresh_token")
        and bool(_persistent_session_cookie())
    ):
        if _restore_persistent_session():
            st.session_state["token_refresh_status"] = "ok"
            st.session_state["token_refresh_error"] = ""
            return True

        st.session_state["token_refresh_status"] = str(
            st.session_state.get("persistent_session_status") or "unavailable"
        )
        st.session_state["token_refresh_error"] = str(
            st.session_state.get("persistent_session_error")
            or "The secure session cannot be renewed. Please sign in again."
        )
        return False

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
    """Restore auth from memory first, then from the HttpOnly browser session."""
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

    if _restore_persistent_session():
        cached_profile = _cached_profile()
        if cached_profile is not None:
            _sync_profile_to_session(cached_profile)
        return True

    st.session_state["authenticated"] = False
    return False


def get_token() -> str:
    """Return active auth token."""
    if not _raw_token() and not restore_auth():
        return ""

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
    except requests.RequestException:
        return FakeResponse(
            503,
            "The backend is temporarily unavailable. Please try again.",
        )
    except Exception:
        return FakeResponse(
            503,
            "The backend request could not be completed. Please try again.",
        )


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
    except requests.RequestException:
        return FakeResponse(
            503,
            "The backend is temporarily unavailable. Please try again.",
        )
    except Exception:
        return FakeResponse(
            503,
            "The backend request could not be completed. Please try again.",
        )


# =========================
# Profile helpers
# =========================


def _cached_profile() -> dict[str, Any] | None:
    """Return the last successfully loaded profile without contacting the backend."""
    profile = st.session_state.get("profile")
    return profile if isinstance(profile, dict) and profile else None


def get_profile_state() -> str:
    """Return the local profile availability state without making a request."""
    state = str(
        st.session_state.get("profile_availability")
        or PROFILE_STATE_NOT_LOADED
    ).strip().lower()
    return state or PROFILE_STATE_NOT_LOADED


def get_cached_backend_readiness() -> dict[str, Any] | None:
    """Return the last readiness payload without waking the backend."""
    readiness = st.session_state.get("backend_readiness")
    return readiness if isinstance(readiness, dict) and readiness else None


def get_backend_readiness(
    *,
    force: bool = False,
    timeout: int = BACKEND_READINESS_TIMEOUT_SECONDS,
) -> dict[str, Any] | None:
    """Read and cache the backend readiness contract safely.

    A Render instance may be asleep while the browser session is still alive.
    In that case the absence of a readiness response means *unknown*, not an
    unconfigured database, Firebase project, or PayPal account.
    """
    cached = get_cached_backend_readiness()
    checked_at = st.session_state.get("backend_readiness_checked_at")

    try:
        age = time.time() - float(checked_at or 0)
    except (TypeError, ValueError):
        age = float("inf")

    if not force and age <= BACKEND_READINESS_CACHE_SECONDS:
        # A recent failed check is also cached.  Returning ``None`` here keeps
        # one Streamlit rerun from issuing the same cold-start request twice.
        return cached

    try:
        response = requests.get(
            _build_url("/readyz"),
            timeout=timeout,
        )
    except requests.RequestException:
        st.session_state["backend_readiness_status"] = "unavailable"
        st.session_state["backend_readiness_error"] = (
            "The backend readiness check is temporarily unavailable."
        )
        st.session_state["backend_readiness_checked_at"] = time.time()
        return cached

    try:
        payload = response.json()
    except (TypeError, ValueError):
        payload = None

    if not isinstance(payload, Mapping):
        st.session_state["backend_readiness_status"] = "invalid_response"
        st.session_state["backend_readiness_error"] = (
            "The backend returned an invalid readiness response."
        )
        st.session_state["backend_readiness_checked_at"] = time.time()
        return cached

    readiness = dict(payload)
    status = str(readiness.get("status") or "").strip().lower()
    if response.status_code == 200 and status == "ready":
        readiness_status = "ready"
    elif response.status_code in TRANSIENT_PROFILE_STATUS_CODES or status in {
        "not_ready",
        "degraded",
    }:
        readiness_status = "not_ready"
    else:
        readiness_status = f"http_{response.status_code}"

    st.session_state["backend_readiness"] = readiness
    st.session_state["backend_readiness_status"] = readiness_status
    st.session_state["backend_readiness_error"] = ""
    st.session_state["backend_readiness_checked_at"] = time.time()
    return readiness


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


def refresh_profile(*, force: bool = False) -> dict[str, Any] | None:
    """
    Reload the authenticated profile and preserve verified data on transient failures.

    A previously validated profile remains authoritative for the active Streamlit
    session when `/me` is temporarily unavailable, rate-limited, or returns a
    server-side error. Authentication failures invalidate the local session and
    require sign-in instead of silently presenting stale authenticated data.

    ``force=True`` is used by an explicit Refresh Profile action. Normal page
    rendering is cooldown-protected so one cold-start failure cannot trigger a
    burst of identical `/me` requests from the sidebar and page components.
    """
    cached_profile = _cached_profile()

    if not is_logged_in():
        st.session_state["profile_last_refresh_status"] = "not_authenticated"
        st.session_state["profile_using_stale_cache"] = bool(cached_profile)
        st.session_state["profile_availability"] = PROFILE_STATE_NOT_AUTHENTICATED
        return cached_profile

    now = time.time()
    last_attempt_at = st.session_state.get("profile_last_attempt_at")
    try:
        attempt_age = now - float(last_attempt_at or 0)
    except (TypeError, ValueError):
        attempt_age = float("inf")

    if not force and attempt_age < PROFILE_REFRESH_COOLDOWN_SECONDS:
        return cached_profile

    st.session_state["profile_last_attempt_at"] = now
    st.session_state["profile_availability"] = PROFILE_STATE_LOADING

    response = api_get("/me", timeout=PROFILE_REQUEST_TIMEOUT_SECONDS)
    status_code = int(getattr(response, "status_code", 503) or 503)

    # Retry an actual transient HTTP response once.  Transport failures are
    # already represented by FakeResponse and are returned immediately so the
    # UI does not wait through two full cold-start timeouts.
    if (
        status_code in TRANSIENT_PROFILE_STATUS_CODES
        and not isinstance(response, FakeResponse)
    ):
        time.sleep(PROFILE_RETRY_DELAY_SECONDS)
        response = api_get("/me", timeout=PROFILE_REQUEST_TIMEOUT_SECONDS)
        status_code = int(getattr(response, "status_code", 503) or 503)

    if status_code != 200:
        st.session_state["profile_last_refresh_at"] = time.time()
        st.session_state["profile_last_refresh_status"] = f"http_{status_code}"
        st.session_state["profile_last_refresh_error"] = _response_error_message(
            response
        )

        if status_code in {401, 403}:
            _mark_auth_expired(
                "Your authentication session is no longer authorized. "
                "Please sign in again."
            )
            st.session_state["profile_availability"] = (
                PROFILE_STATE_REAUTHENTICATION_REQUIRED
            )
            st.session_state["profile_using_stale_cache"] = False
            return None

        st.session_state["profile_availability"] = (
            PROFILE_STATE_STALE if cached_profile else PROFILE_STATE_UNAVAILABLE
        )
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
        st.session_state["profile_availability"] = (
            PROFILE_STATE_STALE if cached_profile else PROFILE_STATE_UNAVAILABLE
        )
        st.session_state["profile_using_stale_cache"] = bool(cached_profile)
        return cached_profile

    if not isinstance(profile, dict) or not profile:
        st.session_state["profile_last_refresh_at"] = time.time()
        st.session_state["profile_last_refresh_status"] = "invalid_profile"
        st.session_state["profile_last_refresh_error"] = (
            "Backend returned an empty or invalid profile."
        )
        st.session_state["profile_availability"] = (
            PROFILE_STATE_STALE if cached_profile else PROFILE_STATE_UNAVAILABLE
        )
        st.session_state["profile_using_stale_cache"] = bool(cached_profile)
        return cached_profile

    st.session_state["profile"] = profile
    st.session_state["profile_last_refresh_at"] = time.time()
    st.session_state["profile_last_verified_at"] = time.time()
    st.session_state["profile_last_refresh_status"] = "ok"
    st.session_state["profile_last_refresh_error"] = ""
    st.session_state["profile_using_stale_cache"] = False
    st.session_state["profile_availability"] = PROFILE_STATE_VERIFIED
    _sync_profile_to_session(profile)
    return profile


def get_profile(
    *,
    load_if_missing: bool = True,
) -> dict[str, Any] | None:
    """Return the cached profile, optionally loading it when no cache exists."""
    cached_profile = _cached_profile()
    if cached_profile is not None:
        if get_profile_state() == PROFILE_STATE_NOT_LOADED:
            st.session_state["profile_availability"] = PROFILE_STATE_VERIFIED
        _sync_profile_to_session(cached_profile)
        return cached_profile

    if not load_if_missing:
        return None

    return refresh_profile()


def load_profile() -> dict[str, Any] | None:
    """Compatibility alias for older imports."""
    return get_profile()


def get_entitlement_state(*, load_if_missing: bool = True) -> str:
    """Return ``pro``, ``free``, ``unknown``, or ``signed_out`` safely."""
    if not is_logged_in():
        return "signed_out"

    profile = get_profile(load_if_missing=load_if_missing)

    if not profile:
        return "unknown"

    return "pro" if _profile_has_pro_access(profile) else "free"


def is_pro_user() -> bool:
    """Check Pro access from the last successfully validated profile."""
    return get_entitlement_state() == "pro"


def is_admin_user(*, load_if_missing: bool = True) -> bool:
    """
    Check administrator access from the last backend-validated profile.

    The frontend never derives administrator access from an email address or
    local session flag. The backend /me response is the authority and exposes
    only the boolean authorization decision.
    """
    profile = get_profile(load_if_missing=load_if_missing)

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


def firebase_register(
    email: str,
    password: str,
    full_name: str = "",
) -> tuple[dict[str, Any] | None, str | None]:
    """Create a Firebase email/password account and return secure credentials."""
    if not FIREBASE_API_KEY:
        return None, "Missing FIREBASE_API_KEY"

    url = (
        "https://identitytoolkit.googleapis.com/"
        f"v1/accounts:signUp?key={FIREBASE_API_KEY}"
    )
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }

    try:
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code != 200:
            try:
                error_data = response.json()
                message = error_data.get("error", {}).get("message", response.text)
            except Exception:
                message = response.text
            return None, str(message)

        firebase_payload = response.json()
        if not isinstance(firebase_payload, dict):
            return None, "Firebase returned invalid registration data."

        display_name = str(full_name or "").strip()
        id_token = str(firebase_payload.get("idToken") or "").strip()
        if display_name and id_token:
            update_url = (
                "https://identitytoolkit.googleapis.com/"
                f"v1/accounts:update?key={FIREBASE_API_KEY}"
            )
            try:
                update_response = requests.post(
                    update_url,
                    json={
                        "idToken": id_token,
                        "displayName": display_name,
                        "returnSecureToken": True,
                    },
                    timeout=60,
                )
                if update_response.status_code == 200:
                    updated_payload = update_response.json()
                    if isinstance(updated_payload, dict):
                        firebase_payload.update(updated_payload)
                else:
                    # Account creation already succeeded. Keep the local
                    # display name for this session; the account remains valid.
                    firebase_payload["displayName"] = display_name
            except (requests.RequestException, TypeError, ValueError):
                # Do not report a successful account creation as a failure just
                # because the optional profile-name update was unavailable.
                firebase_payload["displayName"] = display_name

        return firebase_payload, None
    except requests.RequestException:
        return None, "Firebase registration is temporarily unavailable. Please try again."
    except (TypeError, ValueError):
        return None, "Firebase returned invalid registration data."
