import os

import requests
import streamlit as st

st.set_page_config(
    page_title="Login • TalentMatch Pro",
    page_icon="🔐",
    layout="wide",
)

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "https://talentmatch-backend-1283.onrender.com",
)

FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY", "")

st.title("🔐 Login")
st.caption("Access your TalentMatch Pro account.")

if "user" not in st.session_state:
    st.session_state["user"] = None


def firebase_login(email: str, password: str):
    url = (
        "https://identitytoolkit.googleapis.com/v1/accounts:"
        f"signInWithPassword?key={FIREBASE_API_KEY}"
    )

    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }

    return requests.post(url, json=payload, timeout=30)


with st.container(border=True):
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login", use_container_width=True):
        if not FIREBASE_API_KEY:
            st.error("FIREBASE_API_KEY is missing in Render Environment.")
            st.stop()

        if not email or not password:
            st.error("Please fill all fields.")
            st.stop()

        try:
            response = firebase_login(email, password)
        except Exception as exc:
            st.error(f"Request failed: {exc}")
            st.stop()

        if response.status_code != 200:
            try:
                error_message = response.json().get("error", {}).get("message", response.text)
            except Exception:
                error_message = response.text

            st.error(error_message)
            st.stop()

        data = response.json()

        st.session_state["user"] = {
            "email": data.get("email"),
            "id_token": data.get("idToken"),
            "refresh_token": data.get("refreshToken"),
            "local_id": data.get("localId"),
        }

        st.success("Logged in successfully.")
        st.rerun()

st.divider()

if st.session_state.get("user"):
    st.success(f"Logged in as: {st.session_state['user']['email']}")

    if st.button("Logout", use_container_width=True):
        st.session_state["user"] = None
        st.success("Logged out.")
        st.rerun()