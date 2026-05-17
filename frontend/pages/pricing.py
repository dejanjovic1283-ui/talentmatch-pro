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


def get_auth_headers() -> dict[str, str]:
    user = st.session_state.get("user")

    if not isinstance(user, dict):
        return {}

    token = user.get("id_token") or user.get("idToken") or ""

    if not token:
        return {}

    return {"Authorization": f"Bearer {token}"}


def post_billing_endpoint(endpoint: str) -> dict | None:
    headers = get_auth_headers()

    if not headers:
        st.error("Please login first.")
        return None

    try:
        response = requests.post(
            f"{BACKEND_URL}{endpoint}",
            headers=headers,
            timeout=60,
        )
    except requests.RequestException as exc:
        st.error(f"Billing request failed: {exc}")
        return None

    if response.status_code != 200:
        st.error(response.text)
        return None

    return response.json()


def demo_upgrade() -> None:
    result = post_billing_endpoint("/billing/demo-upgrade")

    if result:
        st.success("Demo Pro upgrade successful.")
        st.balloons()
        st.rerun()


def start_stripe_checkout() -> None:
    result = post_billing_endpoint("/billing/create-checkout")

    if not result:
        return

    checkout_url = result.get("checkout_url")

    if not checkout_url:
        st.error("Stripe checkout URL missing.")
        return

    st.session_state["stripe_checkout_url"] = checkout_url


def open_billing_portal() -> None:
    result = post_billing_endpoint("/billing/create-portal")

    if not result:
        return

    portal_url = result.get("portal_url")

    if not portal_url:
        st.error("Stripe billing portal URL missing.")
        return

    st.session_state["stripe_portal_url"] = portal_url


query_params = st.query_params

if query_params.get("success") == "1":
    st.success("Payment successful. Stripe webhook will unlock Pro shortly.")

if query_params.get("canceled") == "1":
    st.warning("Checkout canceled.")

st.title("🚀 Upgrade to TalentMatch Pro")
st.caption(
    "Unlock unlimited AI CV analysis, PDF reports, CV Rewrite AI, Semantic Matching, and Recruiter Mode."
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
        ❌ Semantic Matching  
        ❌ Recruiter Mode  
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
        ✅ Semantic Matching  
        ✅ Recruiter Mode  
        ✅ Saved history  
        ✅ Candidate ranking  
        ✅ Recruiter-ready reports  

        **$9/month**
        """
    )

    if st.button("💳 Upgrade with Stripe", use_container_width=True):
        start_stripe_checkout()

    checkout_url = st.session_state.get("stripe_checkout_url")

    if checkout_url:
        st.link_button(
            "Continue to secure Stripe checkout",
            checkout_url,
            use_container_width=True,
        )

st.divider()

col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 Demo Upgrade to Pro", use_container_width=True):
        demo_upgrade()

with col2:
    if st.button("⚙️ Manage Billing", use_container_width=True):
        open_billing_portal()

    portal_url = st.session_state.get("stripe_portal_url")

    if portal_url:
        st.link_button(
            "Open Stripe Billing Portal",
            portal_url,
            use_container_width=True,
        )

st.info(
    "Demo upgrade stays available for development. Stripe checkout works after Stripe keys are added in Render."
)