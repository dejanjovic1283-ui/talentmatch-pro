import os
import requests
import streamlit as st

st.set_page_config(
    page_title="Pricing • TalentMatch Pro",
    page_icon="🚀",
    layout="wide",
)

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "https://talentmatch-backend-1283.onrender.com",
).rstrip("/")


def get_token():
    user = st.session_state.get("user")

    if isinstance(user, dict):
        for key in [
            "idToken",
            "id_token",
            "token",
            "accessToken",
            "access_token",
        ]:
            value = user.get(key)
            if value:
                return str(value)

    for key in [
        "id_token",
        "idToken",
        "firebase_token",
        "token",
        "access_token",
    ]:
        value = st.session_state.get(key)
        if value:
            return str(value)

    return ""


def get_headers():
    token = get_token()

    if not token:
        return {}

    return {"Authorization": f"Bearer {token}"}


def get_profile():
    headers = get_headers()

    if not headers:
        return None

    try:
        response = requests.get(
            f"{BACKEND_URL}/me",
            headers=headers,
            timeout=60,
        )

        if response.status_code == 200:
            return response.json()

        return None

    except Exception:
        return None


def post_backend(endpoint):
    headers = get_headers()

    if not headers:
        st.error("Please login first.")
        return None

    try:
        response = requests.post(
            f"{BACKEND_URL}{endpoint}",
            headers=headers,
            timeout=90,
        )

        if response.status_code != 200:
            st.error(response.text)
            return None

        return response.json()

    except Exception as exc:
        st.error(f"Request failed: {exc}")
        return None


params = st.query_params

if params.get("success") == "1":
    st.success(
        "Payment successful. Stripe webhook will unlock Pro shortly. Refresh in a few seconds."
    )

if params.get("canceled") == "1":
    st.warning("Checkout canceled.")

headers = get_headers()
profile = get_profile()

is_logged_in = bool(headers)
is_pro = bool(profile and profile.get("is_pro"))

st.title("🚀 Upgrade to TalentMatch Pro")
st.caption(
    "Unlock unlimited AI CV analysis, PDF reports, CV Rewrite AI, Semantic Matching, and Recruiter Mode."
)

if not is_logged_in:
    st.warning("Please login before upgrading.")

if is_pro:
    st.success("🚀 Pro plan active.")

col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.markdown("## Free")
        st.markdown(
            """
✅ 3 CV analyses  
✅ ATS keyword checker  
✅ TXT export  

❌ PDF reports  
❌ CV Rewrite AI  
❌ Semantic Matching  
❌ Recruiter Mode  
❌ Unlimited analyses  

**$0**
"""
        )

with col2:
    with st.container(border=True):
        st.markdown("## Pro")
        st.markdown(
            """
✅ Unlimited CV analyses  
✅ PDF report export  
✅ CV Rewrite AI  
✅ Semantic Matching  
✅ Recruiter Mode  
✅ Saved history  
✅ Candidate ranking  
✅ Recruiter-ready reports  

**$9/month**
"""
        )

        if is_pro:
            st.success("You already have Pro.")
        else:
            if st.button(
                "💳 Upgrade with Stripe",
                use_container_width=True,
                disabled=not is_logged_in,
            ):
                data = post_backend("/billing/create-checkout")

                if data and data.get("checkout_url"):
                    st.session_state["checkout_url"] = data["checkout_url"]

            if st.session_state.get("checkout_url"):
                st.link_button(
                    "Open Stripe Checkout",
                    st.session_state["checkout_url"],
                    use_container_width=True,
                )

st.divider()

left, right = st.columns(2)

with left:
    if st.button(
        "🚀 Demo Upgrade to Pro",
        use_container_width=True,
        disabled=not is_logged_in,
    ):
        data = post_backend("/billing/demo-upgrade")

        if data:
            st.success("Demo upgrade successful.")
            st.rerun()

with right:
    if st.button(
        "⚙️ Manage Billing",
        use_container_width=True,
        disabled=not is_logged_in,
    ):
        data = post_backend("/billing/create-portal")

        if data and data.get("portal_url"):
            st.session_state["portal_url"] = data["portal_url"]

    if st.session_state.get("portal_url"):
        st.link_button(
            "Open Billing Portal",
            st.session_state["portal_url"],
            use_container_width=True,
        )

st.info(
    "Stripe checkout uses test mode now. Use card 4242 4242 4242 4242, expiry 12/34, CVC 123."
)

with st.expander("Debug auth state"):
    st.json(
        {
            "backend_url": BACKEND_URL,
            "logged_user_detected": is_logged_in,
            "auth_headers_detected": bool(headers),
            "profile_loaded": bool(profile),
            "is_pro": is_pro,
            "profile": profile,
            "session_state_keys": list(st.session_state.keys()),
        }
    )