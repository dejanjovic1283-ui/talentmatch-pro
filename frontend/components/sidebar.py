from __future__ import annotations

from datetime import datetime

import streamlit as st

from auth_utils import clear_auth, is_logged_in, is_pro_user, refresh_profile
from components.ui import get_display_name, get_initials, safe_html


APP_VERSION = "v1.0"


def _sidebar_css() -> None:
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] {
            background:
                radial-gradient(circle at top left, rgba(37, 99, 235, 0.24), transparent 32%),
                radial-gradient(circle at bottom right, rgba(16, 185, 129, 0.18), transparent 34%),
                linear-gradient(180deg, #0f172a 0%, #111827 48%, #020617 100%);
            border-right: 1px solid rgba(148, 163, 184, 0.20);
        }

        section[data-testid="stSidebar"] * {
            color: #e5e7eb;
        }

        section[data-testid="stSidebar"] hr {
            border-color: rgba(148, 163, 184, 0.25);
            margin: 0.95rem 0;
        }

        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            color: #cbd5e1;
        }

        section[data-testid="stSidebar"] a {
            border-radius: 15px;
            padding: 0.24rem 0.45rem;
            font-weight: 800;
            border: 1px solid transparent;
            transition: all 0.16s ease;
        }

        section[data-testid="stSidebar"] a:hover {
            background: rgba(37, 99, 235, 0.18);
            border-color: rgba(96, 165, 250, 0.20);
            transform: translateX(2px);
        }

        section[data-testid="stSidebar"] .stButton > button {
            border-radius: 15px !important;
            font-weight: 900 !important;
            border: 1px solid rgba(148, 163, 184, 0.24) !important;
            background: rgba(15, 23, 42, 0.66) !important;
            color: #f8fafc !important;
            transition: all 0.16s ease !important;
        }

        section[data-testid="stSidebar"] .stButton > button:hover {
            border-color: rgba(96, 165, 250, 0.42) !important;
            background: rgba(37, 99, 235, 0.20) !important;
            transform: translateY(-1px);
        }

        .tm-side-brand {
            padding: 1.08rem 0.95rem 1rem 0.95rem;
            border: 1px solid rgba(148, 163, 184, 0.23);
            border-radius: 26px;
            background:
                radial-gradient(circle at top left, rgba(37, 99, 235, 0.28), transparent 42%),
                radial-gradient(circle at bottom right, rgba(16, 185, 129, 0.18), transparent 44%),
                rgba(15, 23, 42, 0.88);
            box-shadow: 0 20px 52px rgba(0, 0, 0, 0.28);
            margin: 0.35rem 0 1rem 0;
        }

        .tm-side-logo-row {
            display: flex;
            align-items: center;
            gap: 0.78rem;
            margin-bottom: 0.65rem;
        }

        .tm-side-logo {
            width: 54px;
            height: 54px;
            border-radius: 19px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.75rem;
            background: linear-gradient(135deg, #2563eb, #10b981);
            box-shadow: 0 16px 36px rgba(37, 99, 235, 0.35);
            border: 1px solid rgba(255, 255, 255, 0.18);
        }

        .tm-side-title {
            font-size: 1.27rem;
            font-weight: 950;
            letter-spacing: -0.035em;
            color: #f8fafc !important;
            line-height: 1.08;
        }

        .tm-side-subtitle {
            color: #94a3b8 !important;
            font-size: 0.82rem;
            line-height: 1.42;
        }

        .tm-side-user {
            padding: 1rem;
            border-radius: 24px;
            background:
                linear-gradient(135deg, rgba(37, 99, 235, 0.25), rgba(16, 185, 129, 0.16)),
                rgba(15, 23, 42, 0.70);
            border: 1px solid rgba(148, 163, 184, 0.25);
            margin: 0.35rem 0 1rem 0;
            box-shadow: 0 18px 44px rgba(0, 0, 0, 0.18);
        }

        .tm-side-user-top {
            display: flex;
            align-items: center;
            gap: 0.78rem;
        }

        .tm-side-avatar-wrap {
            position: relative;
            width: 58px;
            min-width: 58px;
            height: 58px;
        }

        .tm-side-avatar {
            width: 58px;
            height: 58px;
            border-radius: 21px;
            background: linear-gradient(135deg, #60a5fa, #34d399);
            color: white !important;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 950;
            font-size: 1.06rem;
            box-shadow: 0 16px 34px rgba(16, 185, 129, 0.25);
            border: 1px solid rgba(255, 255, 255, 0.24);
        }

        .tm-side-avatar-badge {
            position: absolute;
            right: -9px;
            bottom: -6px;
            padding: 0.12rem 0.36rem;
            border-radius: 999px;
            background: linear-gradient(135deg, #fbbf24, #f97316);
            color: #111827 !important;
            font-size: 0.58rem;
            font-weight: 950;
            border: 2px solid #0f172a;
            letter-spacing: 0.04em;
        }

        .tm-side-welcome-small {
            color: #93c5fd !important;
            font-size: 0.72rem;
            font-weight: 950;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.15rem;
        }

        .tm-side-welcome {
            font-weight: 950;
            color: #f8fafc !important;
            line-height: 1.16;
            font-size: 0.98rem;
            word-break: break-word;
        }

        .tm-side-plan-row {
            margin-top: 0.78rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.6rem;
        }

        .tm-side-plan {
            display: inline-block;
            padding: 0.22rem 0.62rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.12);
            color: #bfdbfe !important;
            font-size: 0.72rem;
            font-weight: 950;
            letter-spacing: 0.035em;
            white-space: nowrap;
        }

        .tm-side-sync {
            color: #94a3b8 !important;
            font-size: 0.72rem;
            font-weight: 750;
            white-space: nowrap;
        }

        .tm-side-section {
            color: #94a3b8 !important;
            font-size: 0.70rem;
            font-weight: 950;
            letter-spacing: 0.115em;
            text-transform: uppercase;
            margin: 1.05rem 0 0.40rem 0;
        }

        .tm-side-mini-card {
            margin-top: 0.95rem;
            padding: 0.92rem;
            border-radius: 20px;
            background: rgba(15, 23, 42, 0.66);
            border: 1px solid rgba(148, 163, 184, 0.18);
            box-shadow: 0 14px 34px rgba(0, 0, 0, 0.16);
        }

        .tm-side-mini-title {
            color: #f8fafc !important;
            font-size: 0.88rem;
            font-weight: 950;
            margin-bottom: 0.5rem;
        }

        .tm-side-status-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.6rem;
            padding: 0.18rem 0;
            color: #cbd5e1 !important;
            font-size: 0.76rem;
            font-weight: 760;
        }

        .tm-side-dot {
            display: inline-block;
            width: 0.55rem;
            height: 0.55rem;
            border-radius: 999px;
            background: #22c55e;
            box-shadow: 0 0 0 4px rgba(34, 197, 94, 0.12);
            margin-right: 0.35rem;
        }

        .tm-side-footer {
            margin-top: 0.9rem;
            padding: 0.9rem;
            border-radius: 20px;
            background:
                radial-gradient(circle at top left, rgba(37, 99, 235, 0.16), transparent 44%),
                rgba(15, 23, 42, 0.64);
            border: 1px solid rgba(148, 163, 184, 0.18);
            color: #94a3b8 !important;
            font-size: 0.76rem;
            line-height: 1.42;
        }

        .tm-side-footer b {
            color: #f8fafc !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_brand() -> None:
    st.markdown(
        """
        <div class="tm-side-brand">
            <div class="tm-side-logo-row">
                <div class="tm-side-logo">🎯</div>
                <div>
                    <div class="tm-side-title">TalentMatch Pro</div>
                    <div class="tm-side-subtitle">AI Resume Intelligence</div>
                </div>
            </div>
            <div class="tm-side-subtitle">
                ATS optimization • semantic matching • recruiter reports
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_user_panel() -> None:
    if is_logged_in():
        name = get_display_name()
        initials = get_initials(name)
        plan = "PRO" if is_pro_user() else "FREE"
        membership = "Premium Member" if is_pro_user() else "Starter Workspace"
        badge = "PRO" if is_pro_user() else "FREE"
        sync_label = datetime.utcnow().strftime("%H:%M UTC")
    else:
        name = "Guest"
        initials = "TM"
        plan = "SIGN IN"
        membership = "Create account"
        badge = "TM"
        sync_label = "Not signed in"

    st.markdown(
        f"""
        <div class="tm-side-user">
            <div class="tm-side-user-top">
                <div class="tm-side-avatar-wrap">
                    <div class="tm-side-avatar">{safe_html(initials)}</div>
                    <div class="tm-side-avatar-badge">{safe_html(badge)}</div>
                </div>
                <div>
                    <div class="tm-side-welcome-small">Welcome back</div>
                    <div class="tm-side-welcome">{safe_html(name)}</div>
                    <div class="tm-side-subtitle">{safe_html(membership)}</div>
                </div>
            </div>
            <div class="tm-side-plan-row">
                <span class="tm-side-plan">{safe_html(plan)} ACCOUNT</span>
                <span class="tm-side-sync">Sync: {safe_html(sync_label)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _section(title: str) -> None:
    st.markdown(
        f'<div class="tm-side-section">{safe_html(title)}</div>',
        unsafe_allow_html=True,
    )


def _render_navigation() -> None:
    _section("Workspace")
    st.page_link("app.py", label="🏠 Dashboard")
    st.page_link("pages/cv_analysis.py", label="📄 CV Analysis")
    st.page_link("pages/ats_checker.py", label="📋 ATS Checker")
    st.page_link("pages/cv_rewrite.py", label="✍ CV Rewrite")

    _section("Pro tools")
    if is_pro_user():
        st.page_link("pages/semantic_match.py", label="🧠 Semantic Match")
        st.page_link("pages/recruiter_mode.py", label="👥 Recruiter Mode")
    else:
        st.page_link("pages/pricing.py", label="🧠 Semantic Match 🔒")
        st.page_link("pages/pricing.py", label="👥 Recruiter Mode 🔒")

    _section("Account")
    st.page_link("pages/history.py", label="📜 History")
    st.page_link("pages/pricing.py", label="💳 Pricing")
    st.page_link("pages/account.py", label="⚙ Account")

    _section("Company")
    st.page_link("pages/about.py", label="ℹ About Us")
    st.page_link("pages/contact.py", label="📬 Contact Us")
    st.page_link("pages/terms.py", label="📃 Terms")
    st.page_link("pages/privacy.py", label="🔒 Privacy")
    st.page_link("pages/refund.py", label="💸 Refund")


def _render_auth_actions() -> None:
    st.divider()

    if is_logged_in():
        if st.button("🔄 Refresh profile", use_container_width=True):
            refresh_profile()
            st.rerun()

        if st.button("🚪 Logout", use_container_width=True):
            clear_auth()
            st.rerun()
    else:
        st.page_link("pages/login.py", label="🔐 Login")
        st.page_link("pages/register.py", label="📝 Register")


def _render_system_health() -> None:
    st.markdown(
        """
        <div class="tm-side-mini-card">
            <div class="tm-side-mini-title">🟢 System Health</div>
            <div class="tm-side-status-row"><span><span class="tm-side-dot"></span>Backend</span><span>Online</span></div>
            <div class="tm-side-status-row"><span><span class="tm-side-dot"></span>Frontend</span><span>Online</span></div>
            <div class="tm-side-status-row"><span><span class="tm-side-dot"></span>Firebase</span><span>Ready</span></div>
            <div class="tm-side-status-row"><span><span class="tm-side-dot"></span>PayPal</span><span>Live</span></div>
            <div class="tm-side-status-row"><span><span class="tm-side-dot"></span>OpenAI</span><span>Ready</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_footer() -> None:
    year = datetime.utcnow().year
    st.markdown(
        f"""
        <div class="tm-side-footer">
            <b>TalentMatch Pro {safe_html(APP_VERSION)}</b><br>
            Production polish • PayPal billing • PDF reports<br>
            Powered by OpenAI<br>
            © {safe_html(year)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    with st.sidebar:
        _sidebar_css()
        _render_brand()
        _render_user_panel()
        _render_navigation()
        _render_auth_actions()
        _render_system_health()
        _render_footer()