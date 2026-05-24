import os
import time
import streamlit as st

from auth_utils import (
    api_post,
    is_logged_in,
    is_pro_user,
    refresh_profile,
)

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "https://talentmatch-backend-1283.onrender.com",
).rstrip("/")

st.set_page_config(page_title="Pricing • TalentMatch Pro", page_icon="🚀", layout="wide")

# Освежи профил ако је пријављен
if is_logged_in():
    refresh_profile()

is_pro = is_pro_user()

# Обрада Stripe параметара из query string-а
success = st.query_params.get("success") == "1"
canceled = st.query_params.get("canceled") == "1"

if success and is_logged_in() and not is_pro:
    with st.spinner("Confirming Stripe payment and unlocking Pro..."):
        for _ in range(10):
            time.sleep(2)
            refresh_profile()
            if is_pro_user():
                st.success("🚀 Pro plan unlocked successfully!")
                st.balloons()
                st.rerun()
    st.warning("Payment successful, but Pro is still syncing. Refresh in a few seconds.")

if success and is_pro_user():
    st.success("🚀 Payment confirmed. Pro plan is active.")

if canceled:
    st.warning("Checkout canceled. You can upgrade anytime.")

st.markdown("# 🚀 Upgrade to TalentMatch Pro")
st.markdown("Unlock unlimited AI CV analysis, PDF reports, CV Rewrite AI, Semantic Matching, Recruiter Mode, and candidate ranking.")

if not is_logged_in():
    st.warning("Please login before upgrading.")
    st.page_link("pages/login.py", label="🔐 Go to Login")

# Прикажи табеле Free vs Pro
free_col, pro_col = st.columns(2)
with free_col:
    with st.container(border=True):
        st.markdown("## Free")
        st.markdown("### $0")
        st.markdown("""
✅ 3 CV analyses  
✅ ATS keyword checker  
✅ TXT export  

❌ PDF reports  
❌ CV Rewrite AI  
❌ Semantic Matching  
❌ Recruiter Mode  
❌ Unlimited analyses  
""")
with pro_col:
    with st.container(border=True):
        st.markdown("## Pro")
        st.markdown("### $9/month")
        st.markdown("""
✅ Unlimited CV analyses  
✅ PDF report export  
✅ CV Rewrite AI  
✅ Semantic Matching  
✅ Recruiter Mode  
✅ Saved history  
✅ Candidate ranking  
✅ Recruiter-ready reports  
""")
        if is_pro:
            st.success("You already have Pro.")
        else:
            if st.button("💳 Upgrade with Stripe", use_container_width=True, disabled=not is_logged_in()):
                resp = api_post("/billing/create-checkout", timeout=60)
                if resp.status_code == 200:
                    data = resp.json()
                    st.session_state["checkout_url"] = data.get("checkout_url")
                else:
                    st.error(resp.text)

            if st.session_state.get("checkout_url"):
                st.link_button("Open Secure Stripe Checkout", st.session_state["checkout_url"], use_container_width=True)

st.divider()

if st.button("⚙️ Manage Billing", use_container_width=True, disabled=not is_logged_in()):
    resp = api_post("/billing/create-portal", timeout=60)
    if resp.status_code == 200:
        portal_url = resp.json().get("portal_url")
        st.session_state["portal_url"] = portal_url
    else:
        st.error(resp.text)

if st.session_state.get("portal_url"):
    st.link_button("Open Stripe Billing Portal", st.session_state["portal_url"], use_container_width=True)
