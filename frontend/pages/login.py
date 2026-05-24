import time

import streamlit as st

from auth_utils import (
    FIREBASE_API_KEY,
    clear_auth,
    firebase_login,
    is_logged_in,
    save_auth,
)


st.set_page_config(
    page_title="Login • TalentMatch Pro",
    page_icon="🔐",
    layout="wide",
)


st.title("🔐 Login")
st.caption("Access your TalentMatch Pro account.")


if is_logged_in():
    email = (
        st.session_state.get("email")
        or st.session_state.get("user_email")
        or st.session_state.get("user", {}).get("email", "")
    )

    st.success(f"Logged in as: {email}")

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
    email_clean = email.strip()

    if not FIREBASE_API_KEY:
        st.error("FIREBASE_API_KEY is missing in Render environment variables.")
        st.stop()

    if not email_clean or not password:
        st.error("Enter email and password.")
        st.stop()

    with st.spinner("Logging in..."):
        data, error = firebase_login(
            email_clean,
            password,
        )

    if error:
        st.error(error)
        st.stop()

    if not data:
        st.error("Login failed. Empty Firebase response.")
        st.stop()

    token = data.get("idToken", "")

    if not token:
        st.error("Login failed. Firebase did not return idToken.")
        st.stop()

    save_auth(
        token=token,
        email=email_clean,
    )

    st.success("Login successful.")

    time.sleep(1)

    st.switch_page("app.py")