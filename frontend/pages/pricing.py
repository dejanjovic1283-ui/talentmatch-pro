import json
import streamlit as st
import requests
from firebase_client import auth

BACKEND_URL = st.secrets.get(
    "BACKEND_URL",
    "https://talentmatch-backend-1283.onrender.com"
)

st.set_page_config(page_title="Pricing", page_icon="🚀", layout="wide")

st.title("🚀 Upgrade to TalentMatch Pro")

st.write(
    "Unlock unlimited AI CV analysis, PDF reports, CV Rewrite AI, "
    "Semantic Matching, and Recruiter Mode."
)

# =========================================================
# AUTH
# =========================================================

id_token = st.session_state.get("id_token")
user_email = st.session_state.get("user_email")

headers = {}

if id_token:
    headers["Authorization"] = f"Bearer {id_token}"

logged_in = bool(id_token)

# =========================================================
# LOAD PROFILE
# =========================================================

profile = None
is_pro = False
plan = "free"

if logged_in:
    try:
        response = requests.get(
            f"{BACKEND_URL}/me",
            headers=headers,
            timeout=30,
        )

        if response.status_code == 200:
            profile = response.json()
            is_pro = bool(profile.get("is_pro"))
            plan = profile.get("plan", "free")

    except Exception as e:
        st.error(f"Could not load profile: {e}")

# =========================================================
# SUCCESS MESSAGE
# =========================================================

query_params = st.query_params

if query_params.get("success") == "1":
    st.success(
        "Payment successful. Your Pro plan should unlock automatically."
    )

# =========================================================
# WARNING
# =========================================================

if not logged_in:
    st.warning("Please login before upgrading.")

# =========================================================
# DEBUG
# =========================================================

with st.expander("Debug auth state"):
    st.json({
        "backend_url": BACKEND_URL,
        "logged_user_detected": logged_in,
        "auth_headers_detected": bool(headers),
        "profile_loaded": bool(profile),
        "is_pro": is_pro,
        "plan": plan,
        "session_state_keys": list(st.session_state.keys()),
    })

# =========================================================
# PLANS
# =========================================================

col1, col2 = st.columns(2)

with col1:
    st.subheader("Free")

    st.markdown("""
✅ 3 CV analyses  
✅ ATS keyword checker  
✅ TXT export  

❌ PDF reports  
❌ CV Rewrite AI  
❌ Semantic Matching  
❌ Recruiter Mode  
❌ Unlimited analyses  

### $0
""")

with col2:
    st.subheader("Pro")

    st.markdown("""
✅ Unlimited CV analyses  
✅ PDF report export  
✅ CV Rewrite AI  
✅ Semantic Matching  
✅ Recruiter Mode  
✅ Saved history  
✅ Candidate ranking  
✅ Recruiter-ready reports  

### $9/month
""")

# =========================================================
# BUTTONS
# =========================================================

col3, col4 = st.columns(2)

with col3:

    if is_pro:
        st.success("You already have Pro access.")
    else:

        if st.button(
            "💳 Upgrade with Stripe",
            use_container_width=True,
            disabled=not logged_in,
        ):

            try:
                response = requests.post(
                    f"{BACKEND_URL}/billing/create-checkout",
                    headers=headers,
                    timeout=60,
                )

                if response.status_code != 200:
                    st.error(response.text)

                else:
                    data = response.json()
                    checkout_url = data.get("checkout_url")

                    if checkout_url:
                        st.link_button(
                            "Open Stripe Checkout",
                            checkout_url,
                            use_container_width=True,
                        )
                    else:
                        st.error("Stripe checkout URL missing.")

            except Exception as e:
                st.error(f"Checkout failed: {e}")

with col4:

    if is_pro:

        if st.button(
            "⚙️ Manage Billing",
            use_container_width=True,
        ):

            try:
                response = requests.post(
                    f"{BACKEND_URL}/billing/create-portal",
                    headers=headers,
                    timeout=60,
                )

                if response.status_code != 200:
                    st.error(response.text)

                else:
                    data = response.json()
                    portal_url = data.get("portal_url")

                    if portal_url:
                        st.link_button(
                            "Open Billing Portal",
                            portal_url,
                            use_container_width=True,
                        )
                    else:
                        st.error("Portal URL missing.")

            except Exception as e:
                st.error(f"Portal failed: {e}")

# =========================================================
# TEST MODE INFO
# =========================================================

st.info(
    "Stripe checkout uses test mode now. "
    "Use card 4242 4242 4242 4242, expiry 12/34, CVC 123."
)