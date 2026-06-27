import os
from datetime import datetime

import requests
import streamlit as st

from auth_utils import clear_auth, is_logged_in, is_pro_user, refresh_profile
from components.sidebar import render_sidebar


st.set_page_config(
    page_title="Account • TalentMatch Pro",
    page_icon="⚙",
    layout="wide",
)

render_sidebar()

APP_VERSION = "v1.0"
BACKEND_URL = os.getenv("BACKEND_URL", "https://api.talentmatchcv.com")


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def get_email() -> str:
    return (
        st.session_state.get("email")
        or st.session_state.get("user_email")
        or st.session_state.get("user", {}).get("email", "")
        or st.session_state.get("profile", {}).get("email", "")
        or ""
    )


def get_user_id() -> str:
    return (
        st.session_state.get("user_id")
        or st.session_state.get("id")
        or st.session_state.get("uid")
        or st.session_state.get("user", {}).get("uid", "")
        or st.session_state.get("profile", {}).get("id", "")
        or ""
    )


def get_display_name(email: str) -> str:
    if st.session_state.get("display_name"):
        return str(st.session_state["display_name"])

    if st.session_state.get("profile", {}).get("name"):
        return str(st.session_state["profile"]["name"])

    if email:
        return email.split("@")[0].replace(".", " ").replace("_", " ").title()

    return "there"


def get_initials(name: str, email: str) -> str:
    base = name or email or "U"
    parts = base.replace("@", " ").replace(".", " ").replace("_", " ").split()
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[1][0]}".upper()
    return base[:2].upper()


def check_backend_status() -> tuple[str, str]:
    try:
        response = requests.get(f"{BACKEND_URL}/healthz", timeout=6)
        if response.status_code == 200:
            return "Online", "✅"
        return "Degraded", "⚠️"
    except Exception:
        return "Offline", "❌"


def get_usage_summary() -> dict:
    return {
        "CV Analysis": int(st.session_state.get("usage_cv_analysis", 0)),
        "ATS Checker": int(st.session_state.get("usage_ats_checker", 0)),
        "CV Rewrite": int(st.session_state.get("usage_cv_rewrite", 0)),
        "Semantic Match": int(st.session_state.get("usage_semantic_match", 0)),
        "Recruiter Mode": int(st.session_state.get("usage_recruiter_mode", 0)),
    }


def usage_limit_for_plan(is_pro: bool) -> int:
    return 50 if is_pro else 3


def css():
    st.markdown(
        """
        <style>
        .account-hero {
            padding: 2rem;
            border: 1px solid rgba(148, 163, 184, 0.25);
            border-radius: 24px;
            background: linear-gradient(135deg, rgba(59,130,246,0.10), rgba(16,185,129,0.08));
            margin-bottom: 1.5rem;
        }

        .account-title {
            font-size: 3rem;
            font-weight: 800;
            color: #1f2937;
            margin-bottom: 0.4rem;
        }

        .account-subtitle {
            font-size: 1.1rem;
            color: #64748b;
        }

        .tm-card {
            padding: 1.5rem;
            border: 1px solid rgba(148, 163, 184, 0.25);
            border-radius: 22px;
            background: rgba(255, 255, 255, 0.45);
            min-height: 230px;
            transition: all 0.2s ease-in-out;
        }

        .tm-card:hover {
            transform: translateY(-3px);
            border-color: rgba(59, 130, 246, 0.45);
            box-shadow: 0 14px 35px rgba(15, 23, 42, 0.08);
        }

        .tm-card-title {
            font-size: 1.45rem;
            font-weight: 800;
            margin-bottom: 1rem;
            color: #1f2937;
        }

        .tm-muted {
            color: #64748b;
            font-size: 0.95rem;
            margin-bottom: 0.2rem;
        }

        .tm-value {
            color: #111827;
            font-size: 1.1rem;
            font-weight: 700;
            word-break: break-word;
        }

        .tm-avatar {
            width: 86px;
            height: 86px;
            border-radius: 50%;
            background: linear-gradient(135deg, #2563eb, #10b981);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2rem;
            font-weight: 900;
            margin-bottom: 1rem;
        }

        .tm-badge-pro {
            display: inline-block;
            padding: 0.35rem 0.75rem;
            border-radius: 999px;
            background: rgba(16,185,129,0.15);
            color: #047857;
            font-weight: 800;
            margin-top: 0.4rem;
        }

        .tm-badge-free {
            display: inline-block;
            padding: 0.35rem 0.75rem;
            border-radius: 999px;
            background: rgba(59,130,246,0.14);
            color: #1d4ed8;
            font-weight: 800;
            margin-top: 0.4rem;
        }

        .tm-status-ok {
            color: #059669;
            font-weight: 800;
        }

        .tm-status-warn {
            color: #d97706;
            font-weight: 800;
        }

        .tm-progress-label {
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.4rem;
            font-weight: 700;
        }

        .tm-footer-card {
            padding: 1.4rem;
            border: 1px solid rgba(148, 163, 184, 0.25);
            border-radius: 22px;
            background: rgba(241, 245, 249, 0.55);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------
# Page
# ------------------------------------------------------------
css()

if is_logged_in():
    refresh_profile()

email = get_email()
user_id = get_user_id()
display_name = get_display_name(email)
initials = get_initials(display_name, email)
is_pro = is_pro_user()
plan_name = "PRO" if is_pro else "FREE"
access_status = "ACTIVE" if is_logged_in() else "NOT SIGNED IN"

backend_status, backend_icon = check_backend_status()
frontend_status = "Online"
frontend_icon = "✅"

usage = get_usage_summary()
total_usage = sum(usage.values())
monthly_limit = usage_limit_for_plan(is_pro)
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


st.markdown(
    f"""
    <div class="account-hero">
        <div class="account-title">👤 Account</div>
        <div class="account-subtitle">
            Welcome back, <b>{display_name}</b> 👋<br>
            Manage your TalentMatch Pro profile, subscription, usage, and security.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# Top cards
# ------------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.markdown(
        f"""
        <div class="tm-card">
            <div class="tm-card-title">👤 Profile</div>
            <div class="tm-avatar">{initials}</div>
            <div class="tm-muted">Email</div>
            <div class="tm-value">{email or "Not signed in"}</div>
            <br>
            <div class="tm-muted">User ID</div>
            <div class="tm-value">{user_id or "Not available"}</div>
            <br>
            <div class="tm-muted">Registered</div>
            <div class="tm-value">{registered_at}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    badge_class = "tm-badge-pro" if is_pro else "tm-badge-free"
    st.markdown(
        f"""
        <div class="tm-card">
            <div class="tm-card-title">💳 Subscription</div>
            <div class="tm-muted">Current Plan</div>
            <div class="tm-value">{plan_name}</div>
            <span class="{badge_class}">{plan_name}</span>
            <br><br>
            <div class="tm-muted">Status</div>
            <div class="tm-value">{access_status}</div>
            <br>
            <div class="tm-muted">Renewal Date</div>
            <div class="tm-value">{renewal_date}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if is_logged_in():
        if is_pro:
            st.info("💎 Pro plan is enabled for your account.")
        else:
            st.page_link("pages/pricing.py", label="🚀 Upgrade to Pro", icon="💳")
    else:
        st.page_link("pages/login.py", label="🔐 Login", icon="🔐")


st.write("")


# ------------------------------------------------------------
# Usage + Security
# ------------------------------------------------------------
col3, col4 = st.columns(2)

with col3:
    st.markdown(
        f"""
        <div class="tm-card">
            <div class="tm-card-title">📊 Usage</div>
            <div class="tm-progress-label">
                <span>Monthly Usage</span>
                <span>{total_usage} / {monthly_limit}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.progress(usage_percent)

    usage_cols = st.columns(5)
    usage_items = list(usage.items())

    for idx, (label, value) in enumerate(usage_items):
        with usage_cols[idx]:
            st.caption(label)
            st.markdown(f"### {value}")

with col4:
    st.markdown(
        """
        <div class="tm-card">
            <div class="tm-card-title">🔒 Security</div>
            <div class="tm-muted">Session</div>
            <div class="tm-value">Secure Firebase session</div>
            <br>
            <div class="tm-muted">Password</div>
            <div class="tm-value">Managed by Firebase Authentication</div>
            <br>
            <div class="tm-muted">Last check</div>
            <div class="tm-value">Session verified</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    sec1, sec2 = st.columns(2)

    with sec1:
        if st.button("🔄 Refresh profile", width="stretch"):
            refresh_profile()
            st.toast("Profile refreshed.", icon="✅")
            st.rerun()

    with sec2:
        if st.button("🚪 Logout", width="stretch"):
            clear_auth()
            st.toast("Logged out.", icon="👋")
            st.rerun()


st.write("")


# ------------------------------------------------------------
# Application status
# ------------------------------------------------------------
st.markdown("## ℹ Application")

app1, app2, app3, app4 = st.columns(4)

with app1:
    st.markdown(
        f"""
        <div class="tm-footer-card">
            <div class="tm-muted">Version</div>
            <div class="tm-value">TalentMatch Pro {APP_VERSION}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with app2:
    st.markdown(
        f"""
        <div class="tm-footer-card">
            <div class="tm-muted">Backend</div>
            <div class="tm-value">{backend_icon} {backend_status}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with app3:
    st.markdown(
        f"""
        <div class="tm-footer-card">
            <div class="tm-muted">Frontend</div>
            <div class="tm-value">{frontend_icon} {frontend_status}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with app4:
    st.markdown(
        f"""
        <div class="tm-footer-card">
            <div class="tm-muted">Checked</div>
            <div class="tm-value">{today}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.divider()


# ------------------------------------------------------------
# Not signed in state
# ------------------------------------------------------------
if not is_logged_in():
    st.warning("You are not signed in.")
    c1, c2 = st.columns(2)

    with c1:
        st.page_link("pages/login.py", label="🔐 Login", icon="🔐")

    with c2:
        st.page_link("pages/register.py", label="📝 Register", icon="📝")