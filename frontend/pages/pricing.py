import os
import time

import streamlit as st

from auth_utils import (
    BACKEND_URL,
    api_post,
    clear_auth,
    get_auth_headers,
    is_logged_in,
    is_pro_user,
    load_profile,
    refresh_profile,
    restore_auth,
)

st.set_page_config(page_title="Pricing • TalentMatch Pro", page_icon="🚀", layout="wide")

restore_auth()
profile = refresh_profile() if is_logged_in() else None

success = st.query_params.get("success") == "1"
canceled = st.query_params.get("canceled") == "1"

if success and is_logged_in() and not is_pro_user():
    with st.spinner("Confirming Stripe payment and unlocking Pro..."):
        for _ in range(15):
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
    st.warning("Checkout canceled.")