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


def parse_error(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text

    detail = payload.get("detail")

    if isinstance(detail, dict):
        return detail.get("message", str(detail))

    if isinstance(detail, str):
        return detail

    return str(payload)


def post_backend(endpoint: str) -> dict | None:
    headers = get_auth_headers()

    if not headers:
        st.error("Please login first.")
        return None

    try:
        response = requests.post(
            f"{BACKEND_URL}{endpoint}",
            headers=headers,
            timeout=90,
        )
    except requests.RequestException as exc:
        st.error(f"Request failed: {exc}")
        return None

    if response.status_code != 200:
        st.error(parse_error(response))
        return None

    return response.json()


def demo_upgrade() -> None:
    result = post_backend("/billing/demo-upgrade")

    if not result:
        return

    st.success("Demo Pro upgrade successful.")
    st.balloons()
    st.rerun()


def create_stripe_checkout() -> None:
    result = post_backend("/billing/create-checkout")

    if not result:
        return

    checkout_url = result.get("checkout_url")

    if not checkout_url:
        st.error("Stripe checkout URL missing.")
        return

    st.session_state["stripe_checkout_url"] = checkout_url


def create_billing_portal() -> None:
    result = post_backend("/billing/create-portal")

    if not result:
        return

    portal_url = result.get("portal_url")

    if not portal_url:
        st.error("Stripe billing portal URL missing.")
        return

    st.session_state["stripe_portal_url"] = portal_url


def get_profile() -> dict | None:
    headers = get_auth_headers()

    if not headers:
        return None

    try:
        response = requests.get(
            f"{BACKEND_URL}/me",
            headers=headers,
            timeout=60,
        )
    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None

    return response.json()


query_params = st.query_params

if query_params.get("success") == "1":
    st.success("Payment successful. Stripe webhook will unlock Pro shortly. Refresh in a few seconds.")

if query_params.get("canceled") == "1":
    st.warning("Checkout canceled.")

profile = get_profile()
is_logged_in = bool(get_auth_headers())
is_pro = bool(profile and profile.get("is_pro"))

st.title("🚀 Upgrade to TalentMatch Pro")
st.caption(
    "Unlock unlimited AI CV analysis, PDF reports, CV Rewrite AI, Semantic Matching, and Recruiter Mode."
)

if not is_logged_in:
    st.warning("Please login before upgrading.")

if is_pro:
    st.success("🚀 Pro plan active.")

free_col, pro_col = st.columns(2)

with free_col:
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

with pro_col:
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
                create_stripe_checkout()

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
    if st.button(
        "🚀 Demo Upgrade to Pro",
        use_container_width=True,
        disabled=not is_logged_in,
    ):
        demo_upgrade()

with col2:
    if st.button(
        "⚙️ Manage Billing",
        use_container_width=True,
        disabled=not is_logged_in,
    ):
        create_billing_portal()

    portal_url = st.session_state.get("stripe_portal_url")

    if portal_url:
        st.link_button(
            "Open Stripe Billing Portal",
            portal_url,
            use_container_width=True,
        )

st.info(
    "Stripe checkout uses test mode now. Use card 4242 4242 4242 4242, expiry 12/34, CVC 123."
)