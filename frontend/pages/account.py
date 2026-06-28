import os
from datetime import datetime

import requests
import streamlit as st

from auth_utils import clear_auth, is_logged_in, is_pro_user, refresh_profile
from components.sidebar import render_sidebar
from components.ui import apply_global_styles, get_display_name, get_initials, get_user_email, render_hero, safe_html


st.set_page_config(page_title="Account • TalentMatch Pro", page_icon="⚙", layout="wide")
apply_global_styles()
render_sidebar()

APP_VERSION = "v1.0"
BACKEND_URL = os.getenv("BACKEND_URL", "https://api.talentmatchcv.com").rstrip("/")


def get_user_id() -> str:
    return (
        st.session_state.get("user_id")
        or st.session_state.get("id")
        or st.session_state.get("uid")
        or st.session_state.get("user", {}).get("uid", "")
        or st.session_state.get("profile", {}).get("id", "")
        or ""
    )


def check_backend_status() -> tuple[str, str]:
    try:
        response = requests.get(f"{BACKEND_URL}/healthz", timeout=6)
        if response.status_code == 200:
            return "Online", "✅"
        return "Degraded", "⚠️"
    except Exception:
        return "Offline", "❌"


def get_usage_summary() -> dict[str, int]:
    return {
        "CV Analysis": int(st.session_state.get("usage_cv_analysis", 0)),
        "ATS Checker": int(st.session_state.get("usage_ats_checker", 0)),
        "CV Rewrite": int(st.session_state.get("usage_cv_rewrite", 0)),
        "Semantic Match": int(st.session_state.get("usage_semantic_match", 0)),
        "Recruiter Mode": int(st.session_state.get("usage_recruiter_mode", 0)),
    }


def usage_limit_for_plan(pro_enabled: bool) -> int:
    return 50 if pro_enabled else 3


def account_card(title: str, rows: list[tuple[str, str]], icon: str = "✨", min_height: int = 250) -> None:
    body = "".join(
        f"<div class='tm-muted'>{safe_html(label)}</div><div style='font-weight:850;color:#0f172a;word-break:break-word;margin-bottom:.7rem'>{safe_html(value)}</div>"
        for label, value in rows
    )
    st.markdown(
        f"""
        <div class="tm-card" style="min-height:{min_height}px">
            <div class="tm-card-title">{safe_html(icon)} {safe_html(title)}</div>
            {body}
        </div>
        """,
        unsafe_allow_html=True,
    )


if is_logged_in():
    refresh_profile()

email = get_user_email()
user_id = get_user_id()
display_name = get_display_name()
initials = get_initials(display_name)
pro_enabled = is_pro_user()
plan_name = "PRO" if pro_enabled else "FREE"
access_status = "ACTIVE" if is_logged_in() else "NOT SIGNED IN"
backend_status, backend_icon = check_backend_status()
usage = get_usage_summary()
total_usage = sum(usage.values())
monthly_limit = usage_limit_for_plan(pro_enabled)
usage_percent = min(int((total_usage / monthly_limit) * 100), 100) if monthly_limit else 0

registered_at = (
    st.session_state.get("created_at")
    or st.session_state.get("registered_at")
    or st.session_state.get("profile", {}).get("created_at")
    or "Not available"
)
renewal_date = (
    st.session_state.get("renewal_date")
    or st.session_state.get("subscription_renewal_date")
    or st.session_state.get("profile", {}).get("renewal_date")
    or "Not available"
)
today = datetime.utcnow().strftime("%Y-%m-%d")

render_hero(
    "Account workspace",
    f"Welcome: {display_name}",
    "Manage your profile, subscription, usage, security and TalentMatch Pro account status.",
    initials,
)

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Plan", plan_name, "PayPal billing ready")
with c2:
    st.metric("Usage", f"{total_usage}/{monthly_limit}", f"{usage_percent}% used")
with c3:
    st.metric("Backend", backend_status, backend_icon)

st.markdown('<div class="tm-section-title">Profile and subscription</div>', unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    account_card(
        "Profile",
        [
            ("User", f"Welcome: {display_name}"),
            ("Email address", email or "Not signed in"),
            ("User ID", user_id or "Not available"),
            ("Registered", str(registered_at)),
        ],
        "👤",
    )
with col2:
    account_card(
        "Subscription",
        [
            ("Current plan", plan_name),
            ("Access status", access_status),
            ("Renewal date", str(renewal_date)),
            ("Billing provider", "PayPal"),
        ],
        "💳",
    )
    if is_logged_in() and pro_enabled:
        st.success("💎 Pro plan is enabled for your account.")
    elif is_logged_in():
        st.page_link("pages/pricing.py", label="🚀 Upgrade to Pro", icon="💳")
    else:
        st.page_link("pages/login.py", label="🔐 Login", icon="🔐")

st.markdown('<div class="tm-section-title">Usage overview</div>', unsafe_allow_html=True)
usage_left, usage_right = st.columns([1.3, 1])
with usage_left:
    st.markdown(
        f"""
        <div class="tm-card">
            <div class="tm-card-title">📊 Monthly usage</div>
            <div class="tm-muted">Total usage across saved frontend counters.</div>
            <div class="tm-value">{total_usage} / {monthly_limit}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(usage_percent)
with usage_right:
    ucols = st.columns(2)
    usage_items = list(usage.items())
    for index, (label, value) in enumerate(usage_items):
        with ucols[index % 2]:
            st.metric(label, value)

st.markdown('<div class="tm-section-title">Security and system</div>', unsafe_allow_html=True)
col3, col4 = st.columns(2)
with col3:
    account_card(
        "Security",
        [
            ("Session", "Secure Firebase session"),
            ("Password", "Managed by Firebase Authentication"),
            ("Last check", "Session verified" if is_logged_in() else "Login required"),
        ],
        "🔒",
        min_height=220,
    )
with col4:
    account_card(
        "System status",
        [
            ("Frontend", "✅ Online"),
            ("Backend", f"{backend_icon} {backend_status}"),
            ("App version", APP_VERSION),
            ("Date", today),
        ],
        "🛰",
        min_height=220,
    )

st.markdown('<div class="tm-section-title">Account actions</div>', unsafe_allow_html=True)
a1, a2, a3 = st.columns(3)
with a1:
    if st.button("🔄 Refresh profile", use_container_width=True):
        refresh_profile()
        st.success("Profile refreshed.")
with a2:
    st.page_link("pages/pricing.py", label="💳 Billing / Pricing")
with a3:
    if is_logged_in() and st.button("🚪 Logout", use_container_width=True):
        clear_auth()
        st.rerun()
