import time
import streamlit as st

from auth_utils import (
    FIREBASE_API_KEY,
    clear_auth,
    firebase_login,
    is_logged_in,
    save_auth,
)

st.set_page_config(page_title="Login • TalentMatch Pro", page_icon="🔐", layout="wide")

st.title("🔐 Login")
st.caption("Access your TalentMatch Pro account.")

if is_logged_in():
    user = st.session_state.get("user", {})
    st.success(f"Logged in as: {user.get('email', '')}")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Go to App", use_container_width=True):
            st.switch_page("app.py")
    with col2:
        if st.button("Logout", use_container_width=True):
            clear_auth()
            st.rerun()
    st.stop()

email = st.text_input("Email")
password = st.text_input("Password", type="password")

if st.button("Login", use_container_width=True):
    if not FIREBASE_API_KEY:
        st.error("FIREBASE_API_KEY is missing in the environment or .streamlit/secrets.toml")
        st.stop()
    if not email.strip() or not password:
        st.error("Enter email and password.")
        st.stop()

    with st.spinner("Logging in..."):
        token, error = firebase_login(email.strip(), password)
    if error:
        st.error(error)
    else:
        st.success("Login successful.")
        time.sleep(1)
        st.switch_page("app.py")