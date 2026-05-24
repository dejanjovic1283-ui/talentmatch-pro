import os
import requests
import streamlit as st

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "https://talentmatch-backend-1283.onrender.com",
).rstrip("/")

FIREBASE_API_KEY = st.secrets.get("FIREBASE_API_KEY", os.getenv("FIREBASE_API_KEY", ""))

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

def save_auth(token: str, user: dict | None = None):
    init_auth_state()
    st.session_state["auth_token"] = token
    if user:
        st.session_state["user"] = user
    st.session_state["logged_in"] = True

def set_auth(token: str, user: dict | None = None):
    save_auth(token, user)

def clear_auth():
    init_auth_state()
    st.session_state["auth_token"] = None
    st.session_state["user"] = None
    st.session_state["profile"] = None
    st.session_state["is_pro"] = False
    st.session_state["logged_in"] = False

def restore_auth():
    # За сада се не користе колачићи; само инициализуј стање
    init_auth_state()
    return None

def get_token():
    init_auth_state()
    return st.session_state.get("auth_token")

def is_logged_in():
    return bool(get_token())

def get_auth_headers():
    token = get_token()
    return {"Authorization": f"Bearer {token}"} if token else {}

def api_get(path: str, timeout: int = 30):
    return requests.get(
        f"{BACKEND_URL}{path}",
        headers=get_auth_headers(),
        timeout=timeout,
    )

def api_post(path: str, json=None, files=None, data=None, timeout: int = 60):
    return requests.post(
        f"{BACKEND_URL}{path}",
        headers=get_auth_headers(),
        json=json,
        files=files,
        data=data,
        timeout=timeout,
    )

def firebase_login(email: str, password: str):
    if not FIREBASE_API_KEY:
        return None, "Missing FIREBASE_API_KEY"

    url = (
        "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
        f"?key={FIREBASE_API_KEY}"
    )
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }
    try:
        response = requests.post(url, json=payload, timeout=30)
        data = response.json()

        if response.status_code != 200:
            return None, data.get("error", {}).get("message", "Login failed")

        token = data.get("idToken")
        user = {
            "email": data.get("email"),
            "localId": data.get("localId"),
        }
        save_auth(token, user)
        refresh_profile()
        return token, None

    except Exception as e:
        return None, str(e)

def refresh_profile():
    init_auth_state()
    if not is_logged_in():
        return None
    try:
        resp = api_get("/me")
        if resp.status_code != 200:
            return None
        profile = resp.json()
        st.session_state["profile"] = profile
        st.session_state["is_pro"] = bool(
            profile.get("is_pro") or profile.get("plan") == "pro"
        )
        return profile
    except Exception:
        return None

def get_profile():
    init_auth_state()
    return st.session_state.get("profile") or refresh_profile()

def load_profile():
    return get_profile()

def is_pro_user():
    profile = get_profile()
    if not profile:
        return False
    return bool(
        profile.get("is_pro")
        or profile.get("pro")
        or profile.get("plan") == "pro"
        or profile.get("subscription_status") in ["active", "trialing"]
    )

# For backward compatibility in other files:
load_config = init_auth_state
restore_auth_from_cookies = restore_auth