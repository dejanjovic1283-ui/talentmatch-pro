import requests
import streamlit as st

st.set_page_config(
    page_title="Register • TalentMatch Pro",
    page_icon="🚀",
    layout="wide",
)

FIREBASE_API_KEY = st.secrets.get("FIREBASE_API_KEY", "")

st.title("🚀 Create Account")
st.caption("Start using TalentMatch Pro.")

if "user" not in st.session_state:
    st.session_state["user"] = None


def firebase_register(email: str, password: str):
    url = (
        "https://identitytoolkit.googleapis.com/v1/accounts:"
        f"signUp?key={FIREBASE_API_KEY}"
    )

    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }

    response = requests.post(url, json=payload, timeout=30)

    return response


with st.container(border=True):
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    confirm_password = st.text_input(
        "Confirm Password",
        type="password",
    )

    if st.button("Create Account", use_container_width=True):
        if not email or not password:
            st.error("Please fill all fields.")
            st.stop()

        if password != confirm_password:
            st.error("Passwords do not match.")
            st.stop()

        if len(password) < 6:
            st.error("Password must be at least 6 characters.")
            st.stop()

        try:
            response = firebase_register(email, password)
        except Exception as exc:
            st.error(f"Request failed: {exc}")
            st.stop()

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_message = (
                    error_data.get("error", {})
                    .get("message", response.text)
                )
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

        st.success("Account created successfully.")
        st.rerun()


st.divider()

st.info(
    "After registration you can immediately use ATS Checker and CV Analysis."
)