import requests
import streamlit as st

from auth_utils import FIREBASE_API_KEY, is_logged_in, save_auth


st.set_page_config(
    page_title="Register • TalentMatch Pro",
    page_icon="🚀",
    layout="wide",
)


st.title("🚀 Create Account")
st.caption("Start using TalentMatch Pro.")


def firebase_register(email: str, password: str) -> tuple[dict | None, str | None]:
    if not FIREBASE_API_KEY:
        return None, "FIREBASE_API_KEY is missing in Render Environment."

    url = (
        "https://identitytoolkit.googleapis.com/v1/accounts:"
        f"signUp?key={FIREBASE_API_KEY}"
    )

    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }

    try:
        response = requests.post(url, json=payload, timeout=60)
    except requests.RequestException as exc:
        return None, f"Firebase request failed: {exc}"

    if response.status_code != 200:
        try:
            error_message = response.json().get("error", {}).get("message", response.text)
        except Exception:
            error_message = response.text

        return None, error_message

    try:
        return response.json(), None
    except Exception:
        return None, "Firebase returned invalid JSON."


if is_logged_in():
    email = (
        st.session_state.get("email")
        or st.session_state.get("user_email")
        or st.session_state.get("user", {}).get("email", "")
    )

    st.success(f"Already logged in as: {email}")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Go to App", use_container_width=True):
            st.switch_page("app.py")

    with col2:
        if st.button("Go to Pricing", use_container_width=True):
            st.switch_page("pages/pricing.py")

    st.stop()


with st.container(border=True):
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    if st.button("Create Account", use_container_width=True):
        email_clean = email.strip().lower()

        if not email_clean or not password or not confirm_password:
            st.error("Please fill all fields.")
            st.stop()

        if password != confirm_password:
            st.error("Passwords do not match.")
            st.stop()

        if len(password) < 6:
            st.error("Password must be at least 6 characters.")
            st.stop()

        with st.spinner("Creating account..."):
            data, error = firebase_register(email_clean, password)

        if error:
            st.error(error)
            st.stop()

        if not data:
            st.error("Registration failed. Empty Firebase response.")
            st.stop()

        token = data.get("idToken", "")

        if not token:
            st.error("Registration failed. Firebase did not return idToken.")
            st.stop()

        save_auth(
            token=token,
            email=email_clean,
        )

        st.success("Account created successfully.")
        st.info("You can now use ATS Checker and CV Analysis.")

        st.switch_page("app.py")


st.divider()
st.info("After registration you can immediately use ATS Checker and CV Analysis.")