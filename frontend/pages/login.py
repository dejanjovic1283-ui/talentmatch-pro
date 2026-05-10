import os
import requests
import streamlit as st

st.set_page_config(page_title="Login • TalentMatch Pro", page_icon="🔐", layout="wide")

FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY", "")

st.title("🔐 Login")
st.caption("Access your TalentMatch Pro account.")

if "user" not in st.session_state:
    st.session_state["user"] = None


def firebase_login(email: str, password: str):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    return requests.post(url, json=payload, timeout=30)


email = st.text_input("Email")
password = st.text_input("Password", type="password")

if st.button("Login", use_container_width=True):
    if not FIREBASE_API_KEY:
        st.error("FIREBASE_API_KEY is missing in Render Environment.")
        st.stop()

    response = firebase_login(email, password)

    if response.status_code != 200:
        st.error(response.text)
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

if isinstance(st.session_state.get("user"), dict):
    st.success(f"Logged in as: {st.session_state['user'].get('email')}")

    if st.button("Logout", use_container_width=True):
        st.session_state["user"] = None
        st.rerun()