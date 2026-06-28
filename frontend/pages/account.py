import os
from datetime import datetime
from typing import Any

import requests
import streamlit as st

from auth_utils import clear_auth, is_logged_in, is_pro_user, refresh_profile
from components.sidebar import render_sidebar
from components.ui import (
    apply_global_styles,
    get_display_name,
    get_initials,
    get_user_email,
    safe_html,
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


def status_dot(status: str) -> str:
    if status.lower() == "online":
        return "🟢"
    if status.lower() == "degraded":
        return "🟡"
    return "🔴"


def render_account_css() -> None:
    st.markdown(
        """
        <style>
        .tm-account-hero {
            position: relative;
            overflow: hidden;
            border-radius: 34px;
            padding: 2.3rem;
            border: 1px solid rgba(148, 163, 184, 0.24);
            background:
                radial-gradient(circle at 10% 0%, rgba(37, 99, 235, 0.20), transparent 33%),
                radial-gradient(circle at 95% 20%, rgba(16, 185, 129, 0.18), transparent 34%),
                linear-gradient(135deg, rgba(255,255,255,0.92), rgba(248,250,252,0.96));
            box-shadow: 0 26px 80px rgba(15, 23, 42, 0.10);
            margin-bottom: 1.4rem;
        }
        .tm-account-hero-grid {
            display: grid;
            grid-template-columns: 1fr 190px;
            gap: 1.5rem;
            align-items: center;
        }
        .tm-welcome-eyebrow {
            color: #2563eb;
            font-weight: 950;
            letter-spacing: .14em;
            text-transform: uppercase;
            font-size: .78rem;
            margin-bottom: .5rem;
        }
        .tm-welcome-title {
            color: #0f172a;
            font-size: 3.25rem;
            line-height: 1.02;
            letter-spacing: -.065em;
            font-weight: 950;
            margin-bottom: .7rem;
        }
        .tm-welcome-subtitle {
            color: #64748b;
            font-size: 1.08rem;
            line-height: 1.55;
            max-width: 780px;
        }
        .tm-avatar-wrap {
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .tm-avatar-premium {
            width: 142px;
            height: 142px;
            border-radius: 999px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 2.7rem;
            font-weight: 950;
            background: linear-gradient(135deg, #2563eb 0%, #7c3aed 48%, #10b981 100%);
            box-shadow: 0 24px 58px rgba(37, 99, 235, .30);
            border: 6px solid rgba(255,255,255,.82);
        }
        .tm-pro-badge {
            position: absolute;
            bottom: 10px;
            right: 14px;
            padding: .38rem .7rem;
            border-radius: 999px;
            color: white;
            font-size: .78rem;
            font-weight: 950;
            background: linear-gradient(135deg, #0f172a, #2563eb);
            border: 2px solid white;
            box-shadow: 0 14px 28px rgba(15,23,42,.18);
        }
        .tm-account-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 1rem;
            margin: 1rem 0 1.4rem;
        }
        .tm-premium-card {
            padding: 1.25rem;
            border-radius: 26px;
            border: 1px solid rgba(148, 163, 184, 0.24);
            background: rgba(255,255,255,0.78);
            box-shadow: 0 18px 48px rgba(15,23,42,.055);
            min-height: 100%;
        }
        .tm-membership-card {
            border-radius: 30px;
            padding: 1.5rem;
            color: white;
            background:
                radial-gradient(circle at top right, rgba(16, 185, 129, .32), transparent 34%),
                linear-gradient(135deg, #0f172a 0%, #1d4ed8 100%);
            box-shadow: 0 24px 64px rgba(29, 78, 216, .22);
            min-height: 100%;
        }
        .tm-card-label {
            color: #64748b;
            font-size: .78rem;
            font-weight: 900;
            letter-spacing: .10em;
            text-transform: uppercase;
            margin-bottom: .35rem;
        }
        .tm-card-value {
            color: #0f172a;
            font-size: 1.9rem;
            letter-spacing: -.05em;
            line-height: 1.05;
            font-weight: 950;
        }
        .tm-card-note {
            margin-top: .35rem;
            color: #64748b;
            font-size: .9rem;
            line-height: 1.35;
        }
        .tm-membership-title {
            font-size: .82rem;
            letter-spacing: .13em;
            font-weight: 950;
            text-transform: uppercase;
            opacity: .82;
            margin-bottom: .5rem;
        }
        .tm-membership-plan {
            font-size: 2.25rem;
            line-height: 1;
            letter-spacing: -.055em;
            font-weight: 950;
            margin-bottom: 1rem;
        }
        .tm-membership-row {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            padding: .56rem 0;
            border-top: 1px solid rgba(255,255,255,.18);
            font-size: .94rem;
        }
        .tm-membership-row span:first-child { opacity: .75; }
        .tm-membership-row span:last-child { font-weight: 850; text-align: right; }
        .tm-progress-track {
            height: 16px;
            border-radius: 999px;
            background: rgba(148,163,184,.18);
            overflow: hidden;
            border: 1px solid rgba(148,163,184,.20);
            margin-top: .9rem;
        }
        .tm-progress-fill {
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, #2563eb, #10b981);
        }
        .tm-check-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: .75rem;
            padding: .66rem 0;
            border-top: 1px solid rgba(148,163,184,.16);
        }
        .tm-check-left {
            color: #0f172a;
            font-weight: 850;
        }
        .tm-check-right {
            color: #64748b;
            font-size: .9rem;
            text-align: right;
        }
        .tm-action-card {
            padding: 1rem;
            border-radius: 22px;
            border: 1px solid rgba(148,163,184,.24);
            background: rgba(255,255,255,.72);
            min-height: 112px;
        }
        @media (max-width: 900px) {
            .tm-account-hero-grid { grid-template-columns: 1fr; }
            .tm-account-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .tm-welcome-title { font-size: 2.35rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_premium_hero(display_name: str, initials: str, plan_name: str, pro_enabled: bool) -> None:
    member_label = "PRO Member" if pro_enabled else "Free Member"
    badge_label = "PRO" if pro_enabled else "FREE"
    st.markdown(
        f"""
        <div class="tm-account-hero">
            <div class="tm-account-hero-grid">
                <div>
                    <div class="tm-welcome-eyebrow">Account workspace</div>
                    <div class="tm-welcome-title">👋 Welcome back,<br>{safe_html(display_name)}</div>
                    <div class="tm-welcome-subtitle">
                        TalentMatch Pro • {safe_html(member_label)} • Manage your profile, usage, subscription,
                        security and account status from one premium workspace.
                    </div>
                </div>
                <div class="tm-avatar-wrap">
                    <div class="tm-avatar-premium">{safe_html(initials)}</div>
                    <div class="tm-pro-badge">{safe_html(badge_label)}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_card(label: str, value: str, note: str, icon: str) -> None:
    st.markdown(
        f"""
        <div class="tm-premium-card">
            <div class="tm-card-label">{safe_html(icon)} {safe_html(label)}</div>
            <div class="tm-card-value">{safe_html(value)}</div>
            <div class="tm-card-note">{safe_html(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_membership_card(
    *,
    plan_name: str,
    access_status: str,
    renewal_date: str,
    total_usage: int,
    monthly_limit: int,
    usage_percent: int,
) -> None:
    st.markdown(
        f"""
        <div class="tm-membership-card">
            <div class="tm-membership-title">💎 {safe_html(plan_name)} Member</div>
            <div class="tm-membership-plan">{safe_html(plan_name)} Plan</div>
            <div class="tm-membership-row"><span>Billing</span><span>PayPal</span></div>
            <div class="tm-membership-row"><span>Status</span><span>{safe_html(access_status.title())}</span></div>
            <div class="tm-membership-row"><span>Renewal</span><span>{safe_html(renewal_date)}</span></div>
            <div class="tm-membership-row"><span>Usage</span><span>{total_usage}/{monthly_limit} • {usage_percent}%</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_usage_card(usage: dict[str, int], total_usage: int, monthly_limit: int, usage_percent: int) -> None:
    usage_rows = "".join(
        f"""
        <div class="tm-check-row">
            <div class="tm-check-left">{safe_html(label)}</div>
            <div class="tm-check-right">{int(value)}</div>
        </div>
        """
        for label, value in usage.items()
    )
    st.markdown(
        f"""
        <div class="tm-premium-card">
            <div class="tm-card-label">📊 Monthly usage</div>
            <div class="tm-card-value">{total_usage} / {monthly_limit}</div>
            <div class="tm-card-note">{usage_percent}% of your monthly workspace allowance used.</div>
            <div class="tm-progress-track">
                <div class="tm-progress-fill" style="width:{usage_percent}%"></div>
            </div>
            <div style="margin-top:.9rem">{usage_rows}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_profile_card(email: str, user_id: str, registered_at: str) -> None:
    rows = [
        ("User email", email or "Not signed in"),
        ("User ID", user_id or "Not available"),
        ("Registered", registered_at),
    ]
    body = "".join(
        f"""
        <div class="tm-check-row">
            <div class="tm-check-left">{safe_html(label)}</div>
            <div class="tm-check-right">{safe_html(value)}</div>
        </div>
        """
        for label, value in rows
    )
    st.markdown(
        f"""
        <div class="tm-premium-card">
            <div class="tm-card-label">👤 Profile details</div>
            <div class="tm-card-value" style="font-size:1.35rem">Account identity</div>
            <div class="tm-card-note">Firebase-authenticated TalentMatch Pro profile.</div>
            <div style="margin-top:.9rem">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_system_card(backend_status: str, backend_icon: str, today: str) -> None:
    status_headline = "System Healthy" if backend_status == "Online" else "System Attention"
    rows = [
        ("Frontend", "Online", "🟢"),
        ("Backend", backend_status, backend_icon),
        ("Database", "Connected", "🟢" if backend_status == "Online" else "🟡"),
        ("OpenAI", "Ready", "🟢" if backend_status == "Online" else "🟡"),
        ("App version", APP_VERSION, "🚀"),
        ("Date", today, "📅"),
    ]
    body = "".join(
        f"""
        <div class="tm-check-row">
            <div class="tm-check-left">{safe_html(icon)} {safe_html(label)}</div>
            <div class="tm-check-right">{safe_html(value)}</div>
        </div>
        """
        for label, value, icon in rows
    )
    st.markdown(
        f"""
        <div class="tm-premium-card">
            <div class="tm-card-label">{safe_html(status_dot(backend_status))} {safe_html(status_headline)}</div>
            <div class="tm-card-value" style="font-size:1.35rem">System status</div>
            <div class="tm-card-note">Live operational snapshot for TalentMatch Pro.</div>
            <div style="margin-top:.9rem">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_security_card(is_signed_in: bool) -> None:
    rows = [
        ("Firebase Authentication", "Verified" if is_signed_in else "Login required", "✅" if is_signed_in else "🔐"),
        ("Secure JWT Session", "Active" if is_signed_in else "Inactive", "✅" if is_signed_in else "⚪"),
        ("HTTPS", "Enabled", "✅"),
        ("PayPal Billing", "Ready", "✅"),
    ]
    body = "".join(
        f"""
        <div class="tm-check-row">
            <div class="tm-check-left">{safe_html(icon)} {safe_html(label)}</div>
            <div class="tm-check-right">{safe_html(value)}</div>
        </div>
        """
        for label, value, icon in rows
    )
    st.markdown(
        f"""
        <div class="tm-premium-card">
            <div class="tm-card-label">🔒 Security center</div>
            <div class="tm-card-value" style="font-size:1.35rem">Protected account</div>
            <div class="tm-card-note">Authentication and billing security checks.</div>
            <div style="margin-top:.9rem">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
    generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return "\n".join(
        [
            "TalentMatch Pro - Account Profile",
            "=" * 34,
            f"Generated: {generated_at}",
            "",
            "Profile",
            "- " * 10,
            f"Name: {display_name}",
            f"Email: {email or 'Not signed in'}",
            f"User ID: {user_id or 'Not available'}",
            "",
            "Subscription",
            "- " * 10,
            f"Plan: {plan_name}",
            f"Status: {access_status}",
            f"Billing: PayPal",
            f"Renewal: {renewal_date}",
            "",
            "Usage",
            "- " * 10,
            f"Monthly usage: {total_usage}/{monthly_limit}",
            "",
            "System",
            "- " * 10,
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
today = datetime.utcnow().strftime("%Y-%m-%d")

render_premium_hero(display_name, initials, plan_name, pro_enabled)

st.markdown('<div class="tm-section-title">Account overview</div>', unsafe_allow_html=True)
st.markdown('<div class="tm-account-grid">', unsafe_allow_html=True)
kpi_cols = st.columns(4)
with kpi_cols[0]:
    render_kpi_card("Total Reports", str(total_usage), "All activity tracked in this workspace.", "📄")
with kpi_cols[1]:
    render_kpi_card("ATS Checks", str(usage.get("ATS Checker", 0)), "Keyword coverage reports.", "🎯")
with kpi_cols[2]:
    render_kpi_card("Semantic Matches", str(usage.get("Semantic Match", 0)), "AI relevance comparisons.", "🧠")
with kpi_cols[3]:
    render_kpi_card("Recruiter Rankings", str(usage.get("Recruiter Mode", 0)), "Candidate ranking workflows.", "🏆")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="tm-section-title">Membership and profile</div>', unsafe_allow_html=True)
membership_col, profile_col = st.columns([1, 1])
with membership_col:
    render_membership_card(
        plan_name=plan_name,
        access_status=access_status,
        renewal_date=renewal_date,
        total_usage=total_usage,
        monthly_limit=monthly_limit,
        usage_percent=usage_percent,
    )
    if is_logged_in() and pro_enabled:
        st.success("💎 Pro plan is enabled for your account.")
    elif is_logged_in():
        st.page_link("pages/pricing.py", label="🚀 Upgrade to Pro", icon="💳")
    else:
        st.page_link("pages/login.py", label="🔐 Login", icon="🔐")
with profile_col:
    render_profile_card(email, user_id, registered_at)

st.markdown('<div class="tm-section-title">Usage and system health</div>', unsafe_allow_html=True)
usage_col, system_col = st.columns([1.1, 1])
with usage_col:
    render_usage_card(usage, total_usage, monthly_limit, usage_percent)
with system_col:
    render_system_card(backend_status, backend_icon, today)

st.markdown('<div class="tm-section-title">Security</div>', unsafe_allow_html=True)
render_security_card(is_logged_in())

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

st.markdown('<div class="tm-section-title">Account actions</div>', unsafe_allow_html=True)
action_cols = st.columns(4)

with action_cols[0]:
    st.markdown(
        """
        <div class="tm-action-card">
            <div class="tm-card-label">🔄 Refresh</div>
            <div class="tm-card-note">Sync latest Firebase and backend profile data.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("🔄 Refresh Profile", use_container_width=True):
        refresh_profile()
        st.success("Profile refreshed.")

with action_cols[1]:
    st.markdown(
        """
        <div class="tm-action-card">
            <div class="tm-card-label">💳 Billing</div>
            <div class="tm-card-note">Open pricing and subscription options.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/pricing.py", label="💳 Manage Subscription")

with action_cols[2]:
    st.markdown(
        """
        <div class="tm-action-card">
            <div class="tm-card-label">📄 Export</div>
            <div class="tm-card-note">Download a simple account profile snapshot.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.download_button(
        "📄 Download Profile",
        data=profile_export.encode("utf-8"),
        file_name="talentmatch_account_profile.txt",
        mime="text/plain",
        use_container_width=True,
    )

with action_cols[3]:
    st.markdown(
        """
        <div class="tm-action-card">
            <div class="tm-card-label">🚪 Session</div>
            <div class="tm-card-note">Securely sign out from this device.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if is_logged_in():
        if st.button("🚪 Logout", use_container_width=True):
            clear_auth()
            st.rerun()
    else:
        st.page_link("pages/login.py", label="🔐 Login")
