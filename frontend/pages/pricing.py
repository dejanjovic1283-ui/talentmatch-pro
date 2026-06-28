import time

import streamlit as st

from auth_utils import api_post, is_logged_in, is_pro_user, refresh_profile
from components.footer import render_footer
from components.sidebar import render_sidebar
from components.ui import apply_global_styles, render_hero


st.set_page_config(page_title="Pricing • TalentMatch Pro", page_icon="🚀", layout="wide")
apply_global_styles()
render_sidebar()

if is_logged_in() and not st.session_state.get("pricing_profile_loaded"):
    refresh_profile()
    st.session_state["pricing_profile_loaded"] = True

is_pro = is_pro_user()
paypal_success = st.query_params.get("paypal_success") == "1"
paypal_cancel = st.query_params.get("paypal_cancel") == "1"

if paypal_success:
    st.success("✅ PayPal subscription approved. We are syncing your Pro access now.")
    if is_logged_in():
        with st.spinner("Refreshing your account status..."):
            for _ in range(5):
                time.sleep(2)
                profile = refresh_profile() or {}
                if (
                    profile.get("is_pro")
                    or profile.get("plan") == "pro"
                    or profile.get("subscription_status") == "active"
                    or profile.get("paypal_subscription_status") == "active"
                ):
                    st.success("🚀 Pro plan is active.")
                    st.balloons()
                    st.rerun()
        st.warning("Payment was approved, but Pro access is still syncing. Please refresh this page in a few moments.")
    else:
        st.info("Please login to verify your Pro status.")

if paypal_cancel:
    st.warning("PayPal checkout was cancelled. You can upgrade anytime.")

render_hero(
    "Simple PayPal pricing",
    "Choose the plan that fits your workflow",
    "Start free, then upgrade to Pro for unlimited AI CV analysis, PDF reports, semantic matching and recruiter workflows.",
    "💳",
)

free_col, pro_col = st.columns(2)
with free_col:
    st.markdown(
        """
        <div class="tm-card">
            <div class="tm-kicker">Starter</div>
            <div class="tm-card-title">Free</div>
            <div class="tm-value">$0/mo</div>
            <div class="tm-muted">For testing the platform and basic ATS checks.</div><br>
            <span class="tm-pill">✅ 3 CV analyses</span>
            <span class="tm-pill">✅ ATS Checker</span>
            <span class="tm-pill">✅ TXT Export</span>
            <span class="tm-pill">❌ PDF Reports</span>
            <span class="tm-pill">❌ Semantic Match</span>
            <span class="tm-pill">❌ Recruiter Mode</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with pro_col:
    st.markdown(
        """
        <div class="tm-card" style="border:1px solid rgba(16,185,129,.45); box-shadow:0 24px 60px rgba(16,185,129,.12)">
            <div class="tm-kicker">Most valuable</div>
            <div class="tm-card-title">Pro</div>
            <div class="tm-value">$9/mo</div>
            <div class="tm-muted">Full AI career workflow for job seekers and recruiter-style screening.</div><br>
            <span class="tm-pill tm-pill-green">✅ Unlimited analyses</span>
            <span class="tm-pill tm-pill-green">✅ PDF Reports</span>
            <span class="tm-pill tm-pill-green">✅ CV Rewrite AI</span>
            <span class="tm-pill tm-pill-green">✅ Semantic Match</span>
            <span class="tm-pill tm-pill-green">✅ Recruiter Mode</span>
            <span class="tm-pill tm-pill-green">✅ Saved History</span>
        </div>
        """,
        unsafe_allow_html=True,
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
                    try:
                        st.json(response.json())
                    except Exception:
                        st.code(response.text)
            else:
                st.error(f"Status: {response.status_code}")
                try:
                    st.json(response.json())
                except Exception:
                    st.code(response.text)
        if st.session_state.get("paypal_portal_url"):
            st.link_button("Open PayPal Subscription Settings", st.session_state["paypal_portal_url"], use_container_width=True)
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
                st.error(f"Status: {response.status_code}")
                try:
                    st.json(response.json())
                except Exception:
                    st.code(response.text)
        if st.session_state.get("paypal_checkout_url"):
            st.link_button("Open Secure PayPal Checkout", st.session_state["paypal_checkout_url"], use_container_width=True)

st.markdown('<div class="tm-section-title">What Pro unlocks</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("### 📥 Branded PDF reports\nExport professional reports with TalentMatch Pro footer and page numbers.")
with c2:
    st.markdown("### 🧠 Semantic matching\nUnderstand meaning, context and gaps beyond exact keywords.")
with c3:
    st.markdown("### 👥 Recruiter workflow\nRank candidates and review hiring-ready insights.")

st.divider()
st.markdown("### 📬 Contact")
st.write("**TalentMatch Pro** · support@talentmatchcv.com · Pro Plan: $9/month via PayPal")
render_footer()
