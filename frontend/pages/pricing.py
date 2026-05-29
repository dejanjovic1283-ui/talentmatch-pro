import time

import streamlit as st

from auth_utils import (
    api_post,
    is_logged_in,
    is_pro_user,
    refresh_profile,
)


st.set_page_config(page_title="Pricing • TalentMatch Pro", page_icon="🚀", layout="wide")


if is_logged_in():
    refresh_profile()

is_pro = is_pro_user()

success = st.query_params.get("success") == "1"
canceled = st.query_params.get("canceled") == "1"


if success and is_logged_in() and not is_pro:
    with st.spinner("Confirming Paddle subscription and unlocking Pro..."):
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
st.markdown(
    "Unlock unlimited AI CV analysis, PDF reports, CV Rewrite AI, "
    "Semantic Matching, Recruiter Mode, and candidate ranking."
)


if not is_logged_in():
    st.warning("Please login before upgrading.")
    st.page_link("pages/login.py", label="🔐 Go to Login")


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
                "💳 Upgrade with Paddle",
                use_container_width=True,
                disabled=not is_logged_in(),
            ):
                with st.spinner("Creating secure Paddle checkout..."):
                    resp = api_post("/billing/create-checkout", timeout=60)

                if resp.status_code == 200:
                    try:
                        data = resp.json()
                    except Exception:
                        st.error("Backend returned invalid checkout response.")
                        st.code(resp.text)
                        st.stop()

                    checkout_url = data.get("checkout_url")

                    if not checkout_url:
                        st.error("Checkout URL missing from backend response.")
                        st.json(data)
                        st.stop()

                    st.session_state["checkout_url"] = checkout_url
                    st.success("Paddle checkout created successfully.")
                else:
                    try:
                        error_payload = resp.json()
                        detail = error_payload.get("detail") or error_payload.get("error") or error_payload
                    except Exception:
                        detail = resp.text

                    st.error(f"Checkout failed: {resp.status_code} - {detail}")

            if st.session_state.get("checkout_url"):
                st.link_button(
                    "Open Secure Paddle Checkout",
                    st.session_state["checkout_url"],
                    use_container_width=True,
                )


st.divider()


if st.button("⚙️ Manage Billing", use_container_width=True, disabled=not is_logged_in()):
    with st.spinner("Opening Paddle billing portal..."):
        resp = api_post("/billing/create-portal", timeout=60)

    if resp.status_code == 200:
        try:
            portal_url = resp.json().get("portal_url")
        except Exception:
            st.error("Backend returned invalid billing portal response.")
            st.code(resp.text)
            st.stop()

        if not portal_url:
            st.warning("Billing portal is not available yet. Complete your first Paddle payment first.")
        else:
            st.session_state["portal_url"] = portal_url
    else:
        try:
            error_payload = resp.json()
            detail = error_payload.get("detail") or error_payload.get("error") or error_payload
        except Exception:
            detail = resp.text

        st.error(f"Billing portal failed: {resp.status_code} - {detail}")


if st.session_state.get("portal_url"):
    st.link_button(
        "Open Paddle Billing Portal",
        st.session_state["portal_url"],
        use_container_width=True,
    )