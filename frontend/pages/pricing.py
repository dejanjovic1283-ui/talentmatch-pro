import time

import streamlit as st

from auth_utils import (
    api_post,
    is_logged_in,
    is_pro_user,
    refresh_profile,
)
from components.footer import render_footer
from components.sidebar import render_sidebar


st.set_page_config(
    page_title="Pricing • TalentMatch Pro",
    page_icon="🚀",
    layout="wide",
)

render_sidebar()

if is_logged_in():
    refresh_profile()

is_pro = is_pro_user()

paypal_success = st.query_params.get("paypal_success") == "1"
paypal_cancel = st.query_params.get("paypal_cancel") == "1"


if paypal_success:
    st.success("✅ PayPal subscription approved. We are syncing your Pro access now.")

    if is_logged_in():
        with st.spinner("Refreshing your account status..."):
            for _ in range(8):
                time.sleep(2)
                profile = refresh_profile() or {}

                if profile.get("is_pro") or profile.get("plan") == "pro":
                    st.success("🚀 Pro plan is active.")
                    st.balloons()
                    st.rerun()

        st.warning(
            "Payment was approved, but Pro access is still syncing. "
            "Please refresh this page in a few moments."
        )
    else:
        st.info("Please login to verify your Pro status.")


if paypal_cancel:
    st.warning("PayPal checkout was cancelled. You can upgrade anytime.")


st.markdown("# 🚀 TalentMatch Pro Pricing")

st.markdown(
    """
Upgrade to **TalentMatch Pro** for unlimited AI-powered CV analysis,
PDF reports, CV Rewrite AI, Semantic Match, Recruiter Mode, and candidate ranking.
"""
)

free_col, pro_col = st.columns(2)

with free_col:
    with st.container(border=True):
        st.markdown("## Free")
        st.markdown("### $0/month")

        st.markdown(
            """
✅ 3 CV analyses

✅ ATS Checker

✅ TXT Export

❌ PDF Reports

❌ CV Rewrite AI

❌ Semantic Match

❌ Recruiter Mode

❌ Unlimited Analyses
"""
        )

with pro_col:
    with st.container(border=True):
        st.markdown("## Pro")
        st.markdown("### $9/month")

        st.markdown(
            """
✅ Unlimited CV Analyses

✅ PDF Reports

✅ CV Rewrite AI

✅ Semantic Match

✅ Recruiter Mode

✅ Candidate Ranking

✅ Saved History

✅ Recruiter Reports
"""
        )

        if not is_logged_in():
            st.warning("Please login before upgrading to Pro.")
            st.page_link("pages/login.py", label="🔐 Go to Login")

        elif is_pro:
            st.success("🚀 You already have Pro.")

            if st.button("💳 Manage PayPal Subscription", use_container_width=True):
                with st.spinner("Opening PayPal subscription management..."):
                    response = api_post("/billing/create-portal", timeout=60)

                if response.status_code == 200:
                    try:
                        portal_url = response.json().get("portal_url")
                    except Exception:
                        portal_url = None

                    if portal_url:
                        st.session_state["paypal_portal_url"] = portal_url
                    else:
                        st.error("PayPal subscription portal URL is missing.")
                else:
                    st.error(f"Billing portal failed: {response.status_code} - {response.text}")

            if st.session_state.get("paypal_portal_url"):
                st.link_button(
                    "Open PayPal Subscription Settings",
                    st.session_state["paypal_portal_url"],
                    use_container_width=True,
                )

        else:
            st.info("Secure monthly subscription powered by PayPal.")

            if st.button("🚀 Upgrade to Pro with PayPal", use_container_width=True):
                with st.spinner("Creating PayPal subscription checkout..."):
                    response = api_post("/billing/create-checkout", timeout=60)

                if response.status_code == 200:
                    try:
                        data = response.json()
                    except Exception:
                        st.error("Backend returned invalid PayPal checkout response.")
                        st.code(response.text)
                        st.stop()

                    checkout_url = data.get("checkout_url")

                    if not checkout_url:
                        st.error("PayPal checkout URL missing from backend response.")
                        st.json(data)
                        st.stop()

                    st.session_state["paypal_checkout_url"] = checkout_url
                    st.success("PayPal checkout created successfully.")
                else:
                    try:
                        error_payload = response.json()
                        detail = (
                            error_payload.get("detail")
                            or error_payload.get("error")
                            or error_payload
                        )
                    except Exception:
                        detail = response.text

                    st.error(f"PayPal checkout failed: {response.status_code} - {detail}")

            if st.session_state.get("paypal_checkout_url"):
                st.link_button(
                    "Open Secure PayPal Checkout",
                    st.session_state["paypal_checkout_url"],
                    use_container_width=True,
                )

st.divider()

st.markdown("## 📬 Contact")

st.markdown(
    """
**TalentMatch Pro**

📧 Email: dejan.jovic1283@gmail.com

🚀 Pro Plan: $9/month via PayPal

💬 Response Time: 24-48 Hours
"""
)

render_footer()
