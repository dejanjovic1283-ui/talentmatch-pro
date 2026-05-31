import streamlit as st

st.title("⚙ Account")

st.subheader("Subscription")

st.info("Current Plan: Free")

st.button("Manage Billing")

st.divider()

st.subheader("Profile")

st.write(st.session_state.get("email"))

if st.button("Logout"):
    st.session_state.clear()
    st.rerun()