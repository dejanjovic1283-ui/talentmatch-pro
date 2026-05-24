import os
import time
from datetime import datetime, timedelta

import requests
import streamlit as st
import extra_streamlit_components as stx


st.set_page_config(page_title="Pricing • TalentMatch Pro", page_icon="🚀", layout="wide")

BACKEND_URL = os.getenv("BACKEND_URL", "https://talentmatch-backend-1283.onrender.com").rstrip("/")
STRIPE_MODE = os.getenv("STRIPE_MODE", "test").lower()
ENABLE_DEMO = os.getenv("ENABLE_DEMO", "false").lower() == "true"


@st.cache_resource
def get_cookie_manager():
    return stx.CookieManager()


cookie_manager = get_cookie_manager()


def restore_auth_from_cookies():
    cookies = cookie_manager.get_all() or {}

    email = cookies.get("tm_email")
    id_token = cookies.get("tm_id_token")
    refresh_token = cookies.get("tm_refresh_token", "")

    if email and id_token:
        st.session_state["user"] = {
            "email": email,
            "idToken": id_token,
            "id_token": id_token,
            "refreshToken": refresh_token,
            "refresh_token": refresh_token,
        }

        st.session_state["firebase_id_token"] = id_token
        st.session_state["id_token"] = id_token
        st.session_state["idToken"] = id_token
        st.session_state["token"] = id_token
        st.session_state["access_token"] = id_token
        st.session_state["refresh_token"] = refresh_token


def get_token():
    restore_auth_from_cookies()

    for key in ["firebase_id_token", "id_token", "idToken", "token", "access_token"]:
        token = st.session_state.get(key)
        if token:
            return str(token)

    user = st.session_state.get("user")

    if isinstance(user, dict):
        for key in ["idToken", "id_token", "token", "accessToken", "access_token"]:
            token = user.get(key)
            if token:
                return str(token)

    return ""


def get_headers():
    token = get_token()
    return {"Authorization": f"Bearer {token}"} if token else {}


def get_profile():
    headers = get_headers()

    if not headers:
        return None

    try:
        response = requests.get(f"{BACKEND_URL}/me", headers=headers, timeout=60)

        if response.status_code == 200:
            profile = response.json()
            st.session_state["profile"] = profile
            return profile

        return None

    except Exception:
        return None


def post_backend(endpoint):
    headers = get_headers()

    if not headers:
        st.error("Please login first.")
        return None

    try:
        response = requests.post(f"{BACKEND_URL}{endpoint}", headers=headers, timeout=90)

        if response.status_code != 200:
            st.error(response.text)
            return None

        return response.json()

    except Exception as exc:
        st.error(f"Request failed: {exc}")
        return None


restore_auth_from_cookies()

params = st.query_params
success = params.get("success") == "1"
canceled = params.get("canceled") == "1"

headers = get_headers()
profile = get_profile()

is_logged_in = bool(headers)
is_pro = bool(
    profile
    and (
        profile.get("is_pro")
        or profile.get("plan") == "pro"
        or profile.get("subscription_status") in ["active", "trialing"]
    )
)

if success and is_logged_in and not is_pro:
    with st.spinner("Confirming Stripe payment and unlocking Pro..."):
        for _ in range(15):
            time.sleep(2)
            profile = get_profile()

            is_pro = bool(
                profile
                and (
                    profile.get("is_pro")
                    or profile.get("plan") == "pro"
                    or profile.get("subscription_status") in ["active", "trialing"]
                )
            )

            if is_pro:
                st.success("🚀 Pro plan unlocked successfully!")
                st.balloons()
                time.sleep(1)
                st.rerun()

    st.warning("Payment was successful, but Pro is still syncing. Refresh in a few seconds.")

if success and is_pro:
    st.success("🚀 Payment confirmed. Pro plan is active.")

if canceled:
    st.warning("Checkout canceled. You can upgrade anytime.")


st.markdown(
    """
# 🚀 Upgrade to TalentMatch Pro

Unlock unlimited AI CV analysis, PDF reports, CV Rewrite AI, Semantic Matching, Recruiter Mode, and candidate ranking.
"""
)

if not is_logged_in:
    st.warning("Please login before upgrading.")

    if st.button("🔐 Go to Login", use_container_width=True):
        st.switch_page("pages/login.py")

if is_pro:
    st.success("🚀 Pro plan active — all premium features are unlocked.")


free_col, pro_col = st.columns(2)

with free_col:
    with st.container(border=True):
        st.markdown("## Free")
        st.markdown("### $0")
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
"""
        )

with pro_col:
    with st.container(border=True):
        st.markdown("## Pro")
        st.markdown("### $9/month")
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
                    "Open Secure Stripe Checkout",
                    st.session_state["checkout_url"],
                    use_container_width=True,
                )

st.divider()

if st.button("⚙️ Manage Billing", use_container_width=True, disabled=not is_logged_in):
    data = post_backend("/billing/create-portal")

    if data and data.get("portal_url"):
        st.session_state["portal_url"] = data["portal_url"]

if st.session_state.get("portal_url"):
    st.link_button(
        "Open Stripe Billing Portal",
        st.session_state["portal_url"],
        use_container_width=True,
    )

if ENABLE_DEMO:
    if st.button("🚀 Demo Upgrade to Pro", use_container_width=True, disabled=not is_logged_in or is_pro):
        data = post_backend("/billing/demo-upgrade")

        if data:
            st.success("Demo upgrade successful.")
            st.balloons()
            st.rerun()

if STRIPE_MODE == "test":
    st.info("Stripe test mode enabled. Use card 4242 4242 4242 4242, expiry 12/34, CVC 123.")