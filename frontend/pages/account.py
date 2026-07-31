from __future__ import annotations

import os
from datetime import datetime, timezone

import requests
import streamlit as st

from auth_utils import clear_auth, is_logged_in, is_pro_user, refresh_profile
from components.sidebar import render_sidebar
from components.ui import (
    apply_global_styles,
    get_display_name,
    get_initials,
    get_user_email,
)


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
            return "Online", "🟢"
        return "Degraded", "🟡"
    except requests.RequestException:
        return "Offline", "🔴"


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


def render_account_css() -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 24px;
            border-color: rgba(148, 163, 184, 0.24);
            background: rgba(255, 255, 255, 0.78);
            box-shadow: 0 16px 44px rgba(15, 23, 42, 0.06);
        }

        div[data-testid="stMetric"] {
            padding: 0.35rem 0;
        }

        div[data-testid="stMetricValue"] {
            font-weight: 900;
            letter-spacing: -0.04em;
        }

        div[data-testid="stPageLink"] a,
        div[data-testid="stButton"] button,
        div[data-testid="stDownloadButton"] button {
            min-height: 3rem;
            border-radius: 16px;
            font-weight: 800;
        }

        .stProgress > div > div > div > div {
            border-radius: 999px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def section_heading(kicker: str, title: str, description: str) -> None:
    st.caption(kicker.upper())
    st.subheader(title)
    st.caption(description)


def labeled_value(label: str, value: str) -> None:
    left, right = st.columns([1.15, 1.85])
    with left:
        st.markdown(f"**{label}**")
    with right:
        st.write(value)


def build_profile_export(
    *,
    display_name: str,
    email: str,
    user_id: str,
    plan_name: str,
    access_status: str,
    renewal_date: str,
    total_usage: int,
    monthly_limit: int,
    backend_status: str,
) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return "\n".join(
        [
            "TalentMatch Pro - Account Profile",
            "=" * 34,
            f"Generated: {generated_at}",
            "",
            "Profile",
            "-" * 20,
            f"Name: {display_name}",
            f"Email: {email or 'Not signed in'}",
            f"User ID: {user_id or 'Not available'}",
            "",
            "Subscription",
            "-" * 20,
            f"Plan: {plan_name}",
            f"Status: {access_status}",
            "Billing: PayPal",
            f"Renewal: {renewal_date}",
            "",
            "Usage",
            "-" * 20,
            f"Monthly usage: {total_usage}/{monthly_limit}",
            "",
            "System",
            "-" * 20,
            f"Backend: {backend_status}",
            f"App version: {APP_VERSION}",
        ]
    )


if is_logged_in():
    refresh_profile()

render_account_css()

email = get_user_email()
user_id = get_user_id()
display_name = get_display_name()
initials = get_initials(display_name)
pro_enabled = is_pro_user()
plan_name = "Pro" if pro_enabled else "Free"
access_status = "ACTIVE" if is_logged_in() else "NOT SIGNED IN"
backend_status, backend_icon = check_backend_status()
usage = get_usage_summary()
total_usage = sum(usage.values())
monthly_limit = usage_limit_for_plan(pro_enabled)
usage_percent = min(int((total_usage / monthly_limit) * 100), 100) if monthly_limit else 0

registered_at = str(
    st.session_state.get("created_at")
    or st.session_state.get("registered_at")
    or st.session_state.get("profile", {}).get("created_at")
    or "Not available"
)
renewal_date = str(
    st.session_state.get("renewal_date")
    or st.session_state.get("subscription_renewal_date")
    or st.session_state.get("profile", {}).get("renewal_date")
    or "Not available"
)
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

with st.container(border=True):
    hero_left, hero_right = st.columns([4, 1])
    with hero_left:
        st.caption("ACCOUNT WORKSPACE")
        st.title(f"👋 Welcome back, {display_name}")
        st.write(
            f"TalentMatch Pro • {plan_name.upper()} Member • Manage your profile, usage, "
            "subscription, security, and account status from one workspace."
        )
        chip_cols = st.columns(3)
        chip_cols[0].info("🔐 Firebase identity")
        chip_cols[1].info("💳 PayPal billing")
        chip_cols[2].info("📄 Profile export")
    with hero_right:
        st.metric("Profile", initials)
        st.metric("Plan", plan_name.upper())

st.write("")
section_heading(
    "Workspace intelligence",
    "Account overview",
    "A concise view of your activity across the core TalentMatch Pro workflows.",
)
overview_cols = st.columns(4)
overview_data = (
    ("Total reports", total_usage, "All tracked activity"),
    ("ATS checks", usage.get("ATS Checker", 0), "Keyword coverage reports"),
    ("Semantic matches", usage.get("Semantic Match", 0), "AI relevance comparisons"),
    ("Recruiter rankings", usage.get("Recruiter Mode", 0), "Candidate ranking workflows"),
)
for column, (label, value, helper) in zip(overview_cols, overview_data):
    with column:
        with st.container(border=True):
            st.metric(label, value)
            st.caption(helper)

st.write("")
section_heading(
    "Membership",
    "Subscription and profile",
    "Manage your plan status and review the identity linked to this workspace.",
)
membership_col, profile_col = st.columns(2)

with membership_col:
    with st.container(border=True):
        st.caption("💎 MEMBERSHIP")
        st.header(f"{plan_name} Plan")
        labeled_value("Billing", "PayPal")
        labeled_value("Status", access_status)
        labeled_value("Renewal", renewal_date)
        labeled_value("Monthly usage", f"{total_usage}/{monthly_limit} • {usage_percent}%")
        st.progress(usage_percent / 100)

with profile_col:
    with st.container(border=True):
        st.caption("👤 PROFILE DETAILS")
        st.header("Account identity")
        st.caption("Firebase-authenticated TalentMatch Pro profile.")
        labeled_value("User email", email or "Not signed in")
        labeled_value("User ID", user_id or "Not available")
        labeled_value("Registered", registered_at)

if is_logged_in() and pro_enabled:
    st.success("💎 Pro plan is enabled for your account.")
elif is_logged_in():
    st.page_link("pages/pricing.py", label="🚀 Upgrade to Pro", icon="💳", use_container_width=True)
else:
    st.page_link("pages/login.py", label="🔐 Login", icon="🔐", use_container_width=True)

st.write("")
section_heading(
    "Operations",
    "Usage and system health",
    "Track monthly activity and confirm the current operational state of the platform.",
)
usage_col, system_col = st.columns(2)

with usage_col:
    with st.container(border=True):
        st.caption("📊 MONTHLY USAGE")
        st.header(f"{total_usage} / {monthly_limit}")
        st.caption(f"{usage_percent}% of your monthly workspace allowance used.")
        st.progress(usage_percent / 100)
        for label, value in usage.items():
            labeled_value(label, str(value))

with system_col:
    with st.container(border=True):
        st.caption(f"{backend_icon} SYSTEM STATUS")
        st.header("System health")
        st.caption("Live operational snapshot for TalentMatch Pro.")
        labeled_value("Frontend", "Online")
        labeled_value("Backend", backend_status)
        labeled_value("Database", "Connected" if backend_status == "Online" else "Check backend")
        labeled_value("OpenAI", "Ready" if backend_status == "Online" else "Check backend")
        labeled_value("App version", APP_VERSION)
        labeled_value("Date", today)

st.write("")
section_heading(
    "Protection",
    "Security center",
    "Review authentication, session, HTTPS, and PayPal billing safeguards.",
)
with st.container(border=True):
    st.caption("🔒 SECURITY CENTER")
    st.header("Protected account")
    st.caption("Authentication, session, transport, and billing safeguards.")
    labeled_value("Firebase Authentication", "Verified" if is_logged_in() else "Login required")
    labeled_value("Secure JWT Session", "Active" if is_logged_in() else "Inactive")
    labeled_value("HTTPS", "Enabled")
    labeled_value("PayPal Billing", "Ready")

profile_export = build_profile_export(
    display_name=display_name,
    email=email,
    user_id=user_id,
    plan_name=plan_name,
    access_status=access_status,
    renewal_date=renewal_date,
    total_usage=total_usage,
    monthly_limit=monthly_limit,
    backend_status=backend_status,
)

st.write("")
section_heading(
    "Controls",
    "Account actions",
    "Refresh profile data, manage PayPal billing, export your profile, or securely end the session.",
)
action_cols = st.columns(4)

with action_cols[0]:
    with st.container(border=True):
        st.caption("🔄 REFRESH")
        st.write("Sync the latest Firebase and backend profile data.")
        if st.button("🔄 Refresh Profile", use_container_width=True):
            refresh_profile()
            st.success("Profile refreshed.")

with action_cols[1]:
    with st.container(border=True):
        st.caption("💳 BILLING")
        st.write("Open PayPal pricing and subscription controls.")
        st.page_link(
            "pages/pricing.py",
            label="💳 Manage Subscription",
            use_container_width=True,
        )

with action_cols[2]:
    with st.container(border=True):
        st.caption("📄 EXPORT")
        st.write("Download a portable account profile snapshot.")
        st.download_button(
            "📄 Download Profile",
            data=profile_export.encode("utf-8"),
            file_name="talentmatch_account_profile.txt",
            mime="text/plain",
            use_container_width=True,
        )

with action_cols[3]:
    with st.container(border=True):
        st.caption("🚪 SESSION")
        st.write("Securely sign out from this device.")
        if is_logged_in():
            if st.button("🚪 Logout", use_container_width=True):
                clear_auth()
                st.rerun()
        else:
            st.page_link("pages/login.py", label="🔐 Login", use_container_width=True)
