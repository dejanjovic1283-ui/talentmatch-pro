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


def demo_upgrade() -> None:
    headers = get_auth_headers()

    if not headers:
        st.error("Please login before upgrading.")
        st.write("DEBUG: No auth headers found.")
        return

    st.write("DEBUG: Sending request to backend...")
    st.write("DEBUG BACKEND_URL:", BACKEND_URL)

    try:
        response = requests.post(
            f"{BACKEND_URL}/billing/demo-upgrade",
            headers=headers,
            timeout=60,
        )
    except requests.RequestException as exc:
        st.error(f"Upgrade request failed: {exc}")
        return

    st.write("STATUS:", response.status_code)

    try:
        st.json(response.json())
    except Exception:
        st.write(response.text)

    if response.status_code == 200:
        st.success("🚀 Account upgraded to Pro.")
        st.balloons()
        st.rerun()
    else:
        st.error("Upgrade failed.")


st.title("🚀 Upgrade to TalentMatch Pro")
st.caption(
    "Unlock unlimited AI CV analysis, PDF reports, CV Rewrite AI, and premium SaaS features."
)

free_col, pro_col = st.columns(2)

with free_col:
    st.container(border=True).markdown(
        """
        ## Free

        ✅ 3 CV analyses  
        ✅ ATS keyword checker  
        ✅ TXT export  

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

    clicked = st.button(
        "🚀 Demo Upgrade to Pro",
        use_container_width=True,
        key="demo_upgrade_button",
    )

    if clicked:
        demo_upgrade()

st.divider()

st.info(
    "Lemon Squeezy checkout will replace demo upgrade after store activation."
)