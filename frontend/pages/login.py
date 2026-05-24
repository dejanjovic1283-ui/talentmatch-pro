import streamlit as st

from auth_utils import FIREBASE_API_KEY, clear_auth, firebase_login, restore_auth, save_auth

st.set_page_config(page_title="Login • TalentMatch Pro", page_icon="🔐", layout="wide")

restore_auth()

st.title("🔐 Login")
st.caption("Access your TalentMatch Pro account.")

current_user = st.session_state.get("user")

if isinstance(current_user, dict) and current_user.get("idToken"):
    st.success(f"Logged in as: {current_user.get('email', '')}")

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
        st.error("FIREBASE_API_KEY is missing in Render Environment.")
        st.stop()

    if not email or not password:
        st.error("Enter email and password.")
        st.stop()

    response = firebase_login(email, password)

    if response.status_code != 200:
        st.error(response.text)
        st.stop()

    data = response.json()

    id_token = data.get("idToken", "")
    refresh_token = data.get("refreshToken", "")
    user_email = data.get("email", email)

    save_auth(user_email, id_token, refresh_token)

    st.success("Logged in successfully.")
    st.switch_page("pages/pricing.py")