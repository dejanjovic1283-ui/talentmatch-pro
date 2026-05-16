import os

import requests
import streamlit as st

st.set_page_config(
    page_title="Upgrade • TalentMatch Pro",
    page_icon="🚀",
    layout="wide",
)

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "https://talentmatch-backend-1283.onrender.com",
).rstrip("/")


def get_auth_headers() -> dict[str, str]:
    user = st.session_state.get("user")

    if not isinstance(user, dict):
        return {}

    token = user.get("id_token") or user.get("idToken") or ""

    if not token:
        return {}

    return {"Authorization": f"Bearer {token}"}


def create_checkout() -> str | None:
    headers = get_auth_headers()

    if not headers:
        st.error("Please login before upgrading.")
        return None

    try:
        response = requests.post(
            f"{BACKEND_URL}/billing/create-checkout",
            headers=headers,
            timeout=60,
        )
    except requests.RequestException as exc:
        st.error(f"Checkout request failed: {exc}")
        return None

    if response.status_code != 200:
        st.error(response.text)
        return None

    data = response.json()
    checkout_url = data.get("checkout_url")

    if not checkout_url:
        st.error("Backend did not return checkout_url.")
        return None

    return checkout_url


st.title("🚀 Upgrade to TalentMatch Pro")
st.caption("Unlock unlimited AI CV analysis, PDF reports, CV Rewrite AI, and premium job application tools.")

free_col, pro_col = st.columns(2)

with free_col:
    st.container(border=True).markdown(
        """
        ## Free

        ✅ 3 CV analyses  
        ✅ Basic AI match score  
        ✅ ATS keyword checker  
        ✅ TXT report export  

        ❌ PDF reports  
        ❌ CV Rewrite AI  
        ❌ Unlimited analyses  

        **$0**
        """
    )

with pro_col:
    st.container(border=True).markdown(
        """
        ## Pro

        ✅ Unlimited CV analyses  
        ✅ PDF report export  
        ✅ CV Rewrite AI  
        ✅ Saved history  
        ✅ Advanced ATS insights  
        ✅ Recruiter-ready reports  

        **$9/month**
        """
    )

    if st.button("🚀 Upgrade to Pro", use_container_width=True):
        checkout_url = create_checkout()

        if checkout_url:
            st.session_state["checkout_url"] = checkout_url
            st.success("Checkout created.")

checkout_url = st.session_state.get("checkout_url")

if checkout_url:
    st.link_button(
        "Continue to secure checkout",
        checkout_url,
        use_container_width=True,
    )

st.divider()

st.info(
    "After successful payment, Lemon Squeezy webhook will upgrade your account to Pro automatically."
)