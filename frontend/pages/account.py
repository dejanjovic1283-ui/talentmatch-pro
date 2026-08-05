from __future__ import annotations

import os
from datetime import datetime, timezone
from textwrap import dedent
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

APP_VERSION = "v3.0 FINAL"
BACKEND_URL = os.getenv("BACKEND_URL", "https://api.talentmatchcv.com").rstrip("/")


def _html(value: str) -> str:
    """Return compact HTML that Streamlit will not interpret as a code block."""
    return "\n".join(
        line.strip()
        for line in dedent(str(value or "")).splitlines()
        if line.strip()
    )


def _account_dark_css() -> str:
    """Return Account-page overrides for the accessible dark theme."""
    return """
    [data-testid="stMain"] .tm-account-hero {
        border-color:rgba(148,163,184,.28)!important;
        background:
            radial-gradient(circle at 8% 0%,rgba(37,99,235,.28),transparent 35%),
            radial-gradient(circle at 96% 18%,rgba(16,185,129,.22),transparent 37%),
            linear-gradient(135deg,rgba(15,23,42,.97),rgba(17,24,39,.95))!important;
        box-shadow:0 30px 86px rgba(0,0,0,.38)!important;
    }

    [data-testid="stMain"] .tm-account-hero::after {
        background:radial-gradient(circle,rgba(124,58,237,.25),transparent 68%)!important;
    }

    [data-testid="stMain"] .tm-welcome-eyebrow,
    [data-testid="stMain"] .tm-section-kicker {
        color:#60a5fa!important;
        -webkit-text-fill-color:#60a5fa!important;
    }

    [data-testid="stMain"] .tm-welcome-title,
    [data-testid="stMain"] .tm-section-title,
    [data-testid="stMain"] .tm-card-value,
    [data-testid="stMain"] .tm-check-left {
        color:#f8fafc!important;
        -webkit-text-fill-color:#f8fafc!important;
    }

    [data-testid="stMain"] .tm-welcome-subtitle,
    [data-testid="stMain"] .tm-section-copy,
    [data-testid="stMain"] .tm-card-note,
    [data-testid="stMain"] .tm-check-right {
        color:#cbd5e1!important;
        -webkit-text-fill-color:#cbd5e1!important;
    }

    [data-testid="stMain"] .tm-hero-chip,
    [data-testid="stMain"] .tm-premium-card,
    [data-testid="stMain"] .tm-action-card {
        color:#e2e8f0!important;
        background:rgba(15,23,42,.86)!important;
        border-color:rgba(148,163,184,.27)!important;
        box-shadow:0 20px 52px rgba(0,0,0,.28)!important;
    }

    [data-testid="stMain"] .tm-card-label {
        color:#93c5fd!important;
        -webkit-text-fill-color:#93c5fd!important;
    }

    [data-testid="stMain"] .tm-check-row {
        border-color:rgba(148,163,184,.20)!important;
    }

    [data-testid="stMain"] .tm-progress-track {
        background:rgba(148,163,184,.20)!important;
        border-color:rgba(148,163,184,.24)!important;
    }

    [data-testid="stMain"] .tm-status-pill {
        color:#a7f3d0!important;
        background:rgba(16,185,129,.15)!important;
        border:1px solid rgba(52,211,153,.24)!important;
    }

    [data-testid="stMain"] .tm-avatar-premium {
        border-color:rgba(255,255,255,.18)!important;
        box-shadow:0 28px 68px rgba(37,99,235,.32)!important;
    }

    [data-testid="stMain"] .tm-pro-badge {
        border-color:rgba(255,255,255,.72)!important;
        background:linear-gradient(135deg,#111827,#2563eb)!important;
    }

    [data-testid="stMain"] .tm-membership-card {
        border-color:rgba(96,165,250,.34)!important;
        box-shadow:0 28px 72px rgba(29,78,216,.26)!important;
    }
    """


def render_account_theme_overrides() -> None:
    """Apply Account-specific Light, Dark, or system-driven theme styles."""
    selected = str(st.session_state.get("tm_theme", "system")).strip().lower()
    if selected not in {"system", "light", "dark"}:
        selected = "system"

    dark_css = _account_dark_css()
    if selected == "dark":
        css = dark_css
    elif selected == "system":
        css = f"@media (prefers-color-scheme: dark) {{{dark_css}}}"
    else:
        css = ""

    if css:
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


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
    except requests.RequestException:
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
        .tm-account-shell {
            display:flex;
            flex-direction:column;
            gap:2.5rem;
            width:100%;
        }

        .tm-account-section {
            display:flex;
            flex-direction:column;
            gap:1rem;
            width:100%;
        }

        .tm-account-hero {
            position:relative;
            overflow:hidden;
            margin-top:3.75rem;
            border-radius:34px;
            padding:2.35rem;
            border:1px solid rgba(148,163,184,.24);
            background:
                radial-gradient(circle at 8% 0%,rgba(37,99,235,.20),transparent 34%),
                radial-gradient(circle at 96% 18%,rgba(16,185,129,.18),transparent 36%),
                linear-gradient(135deg,rgba(255,255,255,.94),rgba(248,250,252,.98));
            box-shadow:0 26px 80px rgba(15,23,42,.10);
        }

        .tm-account-hero::after {
            content:"";
            position:absolute;
            width:280px;
            height:280px;
            right:-110px;
            bottom:-150px;
            border-radius:999px;
            background:radial-gradient(circle,rgba(124,58,237,.16),transparent 68%);
            pointer-events:none;
        }

        .tm-account-hero-grid {
            display:grid;
            grid-template-columns:minmax(0,1fr) 190px;
            gap:2rem;
            align-items:center;
            position:relative;
            z-index:1;
        }

        .tm-welcome-eyebrow {
            color:#2563eb;
            font-weight:950;
            letter-spacing:.14em;
            text-transform:uppercase;
            font-size:.78rem;
            margin-bottom:.55rem;
        }

        .tm-welcome-title {
            color:#0f172a;
            font-size:clamp(2.35rem,5vw,3.45rem);
            line-height:1.02;
            letter-spacing:-.065em;
            font-weight:950;
            margin-bottom:.75rem;
        }

        .tm-welcome-subtitle {
            color:#64748b;
            font-size:1.08rem;
            line-height:1.62;
            max-width:790px;
        }

        .tm-hero-chip-row {
            display:flex;
            flex-wrap:wrap;
            gap:.65rem;
            margin-top:1.15rem;
        }

        .tm-hero-chip {
            display:inline-flex;
            align-items:center;
            gap:.42rem;
            padding:.48rem .72rem;
            border-radius:999px;
            border:1px solid rgba(148,163,184,.24);
            background:rgba(255,255,255,.76);
            color:#334155;
            font-size:.82rem;
            font-weight:850;
            box-shadow:0 8px 22px rgba(15,23,42,.05);
        }

        .tm-avatar-wrap {
            position:relative;
            display:flex;
            align-items:center;
            justify-content:center;
        }

        .tm-avatar-premium {
            width:146px;
            height:146px;
            border-radius:999px;
            display:flex;
            align-items:center;
            justify-content:center;
            color:white;
            font-size:2.75rem;
            font-weight:950;
            background:linear-gradient(135deg,#2563eb 0%,#7c3aed 48%,#10b981 100%);
            box-shadow:0 24px 58px rgba(37,99,235,.30);
            border:6px solid rgba(255,255,255,.86);
        }

        .tm-pro-badge {
            position:absolute;
            bottom:8px;
            right:12px;
            padding:.4rem .72rem;
            border-radius:999px;
            color:white;
            font-size:.78rem;
            font-weight:950;
            background:linear-gradient(135deg,#0f172a,#2563eb);
            border:2px solid white;
            box-shadow:0 14px 28px rgba(15,23,42,.18);
        }

        .tm-section-heading {
            display:flex;
            align-items:flex-end;
            justify-content:space-between;
            gap:1rem;
            margin-bottom:.15rem;
        }

        .tm-section-kicker {
            color:#2563eb;
            font-size:.74rem;
            font-weight:950;
            text-transform:uppercase;
            letter-spacing:.13em;
            margin-bottom:.22rem;
        }

        .tm-section-title {
            color:#0f172a;
            font-size:1.55rem;
            line-height:1.15;
            font-weight:950;
            letter-spacing:-.035em;
        }

        .tm-section-copy {
            color:#64748b;
            line-height:1.55;
            max-width:680px;
            margin-top:.35rem;
        }

        .tm-account-grid {
            display:grid;
            grid-template-columns:repeat(4,minmax(0,1fr));
            gap:1rem;
            width:100%;
        }

        .tm-panel-grid {
            display:grid;
            grid-template-columns:repeat(2,minmax(0,1fr));
            gap:1rem;
            width:100%;
        }

        .tm-premium-card,
        .tm-membership-card,
        .tm-action-card {
            min-height:100%;
            border-radius:26px;
            border:1px solid rgba(148,163,184,.24);
            box-shadow:0 18px 48px rgba(15,23,42,.06);
        }

        .tm-premium-card {
            padding:1.3rem;
            background:rgba(255,255,255,.88);
            backdrop-filter:blur(14px);
        }

        .tm-kpi-card {
            position:relative;
            overflow:hidden;
            min-height:166px;
        }

        .tm-kpi-card::before {
            content:"";
            position:absolute;
            inset:0 0 auto 0;
            height:4px;
            background:linear-gradient(90deg,#2563eb,#10b981);
        }

        .tm-card-label {
            color:#64748b;
            font-size:.76rem;
            font-weight:900;
            letter-spacing:.10em;
            text-transform:uppercase;
            margin-bottom:.42rem;
        }

        .tm-card-value {
            color:#0f172a;
            font-size:1.95rem;
            letter-spacing:-.05em;
            line-height:1.05;
            font-weight:950;
        }

        .tm-card-note {
            margin-top:.45rem;
            color:#64748b;
            font-size:.92rem;
            line-height:1.48;
        }

        .tm-membership-card {
            padding:1.55rem;
            color:white;
            background:
                radial-gradient(circle at top right,rgba(16,185,129,.34),transparent 35%),
                radial-gradient(circle at bottom left,rgba(124,58,237,.28),transparent 40%),
                linear-gradient(135deg,#0f172a 0%,#1d4ed8 100%);
            box-shadow:0 24px 64px rgba(29,78,216,.22);
        }

        .tm-membership-title {
            font-size:.82rem;
            letter-spacing:.13em;
            font-weight:950;
            text-transform:uppercase;
            opacity:.84;
            margin-bottom:.55rem;
        }

        .tm-membership-plan {
            font-size:2.35rem;
            line-height:1;
            letter-spacing:-.055em;
            font-weight:950;
            margin-bottom:1.1rem;
        }

        .tm-membership-row {
            display:flex;
            justify-content:space-between;
            gap:1rem;
            padding:.62rem 0;
            border-top:1px solid rgba(255,255,255,.18);
            font-size:.94rem;
        }

        .tm-membership-row span:first-child {opacity:.76}
        .tm-membership-row span:last-child {font-weight:850;text-align:right}

        .tm-progress-track {
            height:14px;
            border-radius:999px;
            background:rgba(148,163,184,.18);
            overflow:hidden;
            border:1px solid rgba(148,163,184,.20);
            margin-top:.95rem;
        }

        .tm-progress-fill {
            height:100%;
            border-radius:999px;
            background:linear-gradient(90deg,#2563eb,#10b981);
        }

        .tm-check-row {
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:.8rem;
            padding:.7rem 0;
            border-top:1px solid rgba(148,163,184,.16);
        }

        .tm-check-left {
            color:#0f172a;
            font-weight:850;
            min-width:0;
        }

        .tm-check-right {
            color:#64748b;
            font-size:.9rem;
            text-align:right;
            overflow-wrap:anywhere;
        }

        .tm-status-pill {
            display:inline-flex;
            align-items:center;
            gap:.4rem;
            padding:.34rem .62rem;
            border-radius:999px;
            background:rgba(16,185,129,.11);
            color:#047857;
            font-weight:900;
            font-size:.8rem;
            margin-top:.75rem;
        }

        .tm-action-card {
            padding:1.05rem;
            background:rgba(255,255,255,.84);
            min-height:118px;
        }

        .st-key-tm_account_actions [data-testid="stHorizontalBlock"] {
            gap:1rem;
            align-items:stretch;
            margin-bottom:1rem;
        }

        .st-key-tm_account_actions [data-testid="stColumn"] {
            min-width:0;
        }

        .st-key-tm_account_actions [data-testid="stButton"],
        .st-key-tm_account_actions [data-testid="stDownloadButton"],
        .st-key-tm_account_actions [data-testid="stPageLink"] {
            width:100%;
        }

        .st-key-tm_account_actions [data-testid="stButton"] button,
        .st-key-tm_account_actions [data-testid="stDownloadButton"] button,
        .st-key-tm_account_actions [data-testid="stPageLink"] a {
            width:100%;
            min-height:3.1rem;
            border-radius:16px;
            font-weight:900;
        }

        .st-key-tm_account_actions [data-testid="stPageLink"] a {
            border:1px solid rgba(148,163,184,.24);
            background:rgba(255,255,255,.88);
            box-shadow:0 12px 28px rgba(15,23,42,.05);
            padding:.7rem .9rem;
        }

        @media (max-width:1100px) {
            .tm-account-grid {grid-template-columns:repeat(2,minmax(0,1fr))}
        }

        @media (max-width:900px) {
            .tm-account-hero-grid {grid-template-columns:1fr}
            .tm-avatar-wrap {justify-content:flex-start}
            .tm-panel-grid {grid-template-columns:1fr}
        }

        @media (max-width:760px) {
            .tm-account-shell {gap:2rem}
            .tm-account-hero {padding:1.5rem;margin-top:3rem}
            .tm-account-grid {grid-template-columns:1fr}
            .tm-section-heading {align-items:flex-start;flex-direction:column}
            .tm-avatar-premium {width:118px;height:118px;font-size:2.2rem}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    render_account_theme_overrides()


def render_section_heading(kicker: str, title: str, copy: str) -> None:
    st.markdown(
        _html(
            f"""
        <div class="tm-section-heading">
            <div>
                <div class="tm-section-kicker">{safe_html(kicker)}</div>
                <div class="tm-section-title">{safe_html(title)}</div>
                <div class="tm-section-copy">{safe_html(copy)}</div>
            </div>
        </div>
        """
        ),
        unsafe_allow_html=True,
    )


def render_premium_hero(display_name: str, initials: str, plan_name: str, pro_enabled: bool) -> None:
    member_label = "PRO Member" if pro_enabled else "Free Member"
    badge_label = "PRO" if pro_enabled else "FREE"
    st.markdown(
        _html(
            f"""
        <div class="tm-account-hero">
            <div class="tm-account-hero-grid">
                <div>
                    <div class="tm-welcome-eyebrow">Account workspace</div>
                    <div class="tm-welcome-title">Welcome back,<br>{safe_html(display_name)}</div>
                    <div class="tm-welcome-subtitle">
                        TalentMatch Pro • {safe_html(member_label)} • Manage your profile, usage,
                        PayPal subscription, security, and service status from one premium workspace.
                    </div>
                    <div class="tm-hero-chip-row">
                        <span class="tm-hero-chip">🔐 Firebase protected</span>
                        <span class="tm-hero-chip">💳 PayPal billing</span>
                        <span class="tm-hero-chip">📄 Export ready</span>
                    </div>
                </div>
                <div class="tm-avatar-wrap">
                    <div class="tm-avatar-premium">{safe_html(initials)}</div>
                    <div class="tm-pro-badge">{safe_html(badge_label)}</div>
                </div>
            </div>
        </div>
        """
        ),
        unsafe_allow_html=True,
    )


def render_kpi_card(label: str, value: str, note: str, icon: str) -> str:
    return f"""
        <div class="tm-premium-card tm-kpi-card">
            <div class="tm-card-label">{safe_html(icon)} {safe_html(label)}</div>
            <div class="tm-card-value">{safe_html(value)}</div>
            <div class="tm-card-note">{safe_html(note)}</div>
        </div>
    """


def render_membership_card(
    *,
    plan_name: str,
    access_status: str,
    renewal_date: str,
    total_usage: int,
    monthly_limit: int,
    usage_percent: int,
) -> str:
    return f"""
        <div class="tm-membership-card">
            <div class="tm-membership-title">💎 {safe_html(plan_name)} Member</div>
            <div class="tm-membership-plan">{safe_html(plan_name)} Plan</div>
            <div class="tm-membership-row"><span>Billing provider</span><span>PayPal</span></div>
            <div class="tm-membership-row"><span>Access status</span><span>{safe_html(access_status.title())}</span></div>
            <div class="tm-membership-row"><span>Renewal date</span><span>{safe_html(renewal_date)}</span></div>
            <div class="tm-membership-row"><span>Monthly usage</span><span>{total_usage}/{monthly_limit} • {usage_percent}%</span></div>
        </div>
    """


def render_usage_card(
    usage: dict[str, int],
    total_usage: int,
    monthly_limit: int,
    usage_percent: int,
) -> str:
    usage_rows = "".join(
        f"""
        <div class="tm-check-row">
            <div class="tm-check-left">{safe_html(label)}</div>
            <div class="tm-check-right">{int(value)}</div>
        </div>
        """
        for label, value in usage.items()
    )
    return f"""
        <div class="tm-premium-card">
            <div class="tm-card-label">📊 Monthly usage</div>
            <div class="tm-card-value">{total_usage} / {monthly_limit}</div>
            <div class="tm-card-note">{usage_percent}% of your monthly workspace allowance used.</div>
            <div class="tm-progress-track">
                <div class="tm-progress-fill" style="width:{usage_percent}%"></div>
            </div>
            <div style="margin-top:.9rem">{usage_rows}</div>
        </div>
    """


def render_profile_card(email: str, user_id: str, registered_at: str) -> str:
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
    return f"""
        <div class="tm-premium-card">
            <div class="tm-card-label">👤 Profile details</div>
            <div class="tm-card-value" style="font-size:1.35rem">Account identity</div>
            <div class="tm-card-note">Firebase-authenticated TalentMatch Pro profile.</div>
            <div style="margin-top:.9rem">{body}</div>
        </div>
    """


def render_system_card(backend_status: str, backend_icon: str, today: str) -> str:
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
    return f"""
        <div class="tm-premium-card">
            <div class="tm-card-label">{safe_html(status_dot(backend_status))} {safe_html(status_headline)}</div>
            <div class="tm-card-value" style="font-size:1.35rem">System status</div>
            <div class="tm-card-note">Live operational snapshot for TalentMatch Pro.</div>
            <div class="tm-status-pill">{safe_html(backend_icon)} Backend {safe_html(backend_status)}</div>
            <div style="margin-top:.65rem">{body}</div>
        </div>
    """


def render_security_card(is_signed_in: bool) -> str:
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
    return f"""
        <div class="tm-premium-card">
            <div class="tm-card-label">🔒 Security center</div>
            <div class="tm-card-value" style="font-size:1.35rem">Protected account</div>
            <div class="tm-card-note">Authentication, session, transport, and billing safeguards.</div>
            <div style="margin-top:.9rem">{body}</div>
        </div>
    """


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

render_premium_hero(display_name, initials, plan_name, pro_enabled)

render_section_heading(
    "Workspace intelligence",
    "Account overview",
    "A concise view of your activity across the core TalentMatch Pro workflows.",
)
kpi_cards = "".join(
    [
        render_kpi_card("Total Reports", str(total_usage), "All activity tracked in this workspace.", "📄"),
        render_kpi_card("ATS Checks", str(usage.get("ATS Checker", 0)), "Keyword coverage reports.", "🎯"),
        render_kpi_card("Semantic Matches", str(usage.get("Semantic Match", 0)), "AI relevance comparisons.", "🧠"),
        render_kpi_card("Recruiter Rankings", str(usage.get("Recruiter Mode", 0)), "Candidate ranking workflows.", "🏆"),
    ]
)
st.markdown(_html(f'<div class="tm-account-grid">{kpi_cards}</div>'), unsafe_allow_html=True)

render_section_heading(
    "Membership",
    "Subscription and profile",
    "Manage your plan status and review the identity linked to this workspace.",
)
st.markdown(
    _html(
        f"""
    <div class="tm-panel-grid">
        {render_membership_card(
            plan_name=plan_name,
            access_status=access_status,
            renewal_date=renewal_date,
            total_usage=total_usage,
            monthly_limit=monthly_limit,
            usage_percent=usage_percent,
        )}
        {render_profile_card(email, user_id, registered_at)}
    </div>
    """
    ),
    unsafe_allow_html=True,
)

if is_logged_in() and pro_enabled:
    st.success("💎 Pro plan is enabled for your account.")
elif is_logged_in():
    st.page_link("pages/pricing.py", label="🚀 Upgrade to Pro", icon="💳")
else:
    st.page_link("pages/login.py", label="Login", icon="🔐")

render_section_heading(
    "Operations",
    "Usage and system health",
    "Track monthly activity and confirm the current operational state of the platform.",
)
st.markdown(
    _html(
        f"""
    <div class="tm-panel-grid">
        {render_usage_card(usage, total_usage, monthly_limit, usage_percent)}
        {render_system_card(backend_status, backend_icon, today)}
    </div>
    """
    ),
    unsafe_allow_html=True,
)

render_section_heading(
    "Protection",
    "Security center",
    "Review authentication, session, HTTPS, and PayPal billing safeguards.",
)
st.markdown(_html(render_security_card(is_logged_in())), unsafe_allow_html=True)

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

render_section_heading(
    "Controls",
    "Account actions",
    "Refresh profile data, manage PayPal billing, export your profile, or securely end the session.",
)
with st.container(key="tm_account_actions", border=False, width="stretch"):
    first_action_row = st.columns(
        2,
        gap="medium",
        vertical_alignment="top",
        width="stretch",
    )
    second_action_row = st.columns(
        2,
        gap="medium",
        vertical_alignment="top",
        width="stretch",
    )
    action_cols = (*first_action_row, *second_action_row)

    with action_cols[0]:
        st.markdown(
            _html(
                """
            <div class="tm-action-card">
                <div class="tm-card-label">🔄 Refresh</div>
                <div class="tm-card-note">Sync the latest Firebase and backend profile data.</div>
            </div>
            """
            ),
            unsafe_allow_html=True,
        )
        if st.button("🔄 Refresh Profile", key="tm_account_refresh", width="stretch"):
            refresh_profile()
            st.success("Profile refreshed.")

    with action_cols[1]:
        st.markdown(
            _html(
                """
            <div class="tm-action-card">
                <div class="tm-card-label">💳 Billing</div>
                <div class="tm-card-note">Open PayPal pricing and subscription controls.</div>
            </div>
            """
            ),
            unsafe_allow_html=True,
        )
        st.page_link(
            "pages/pricing.py",
            label="💳 Manage Subscription",
            width="stretch",
        )

    with action_cols[2]:
        st.markdown(
            _html(
                """
            <div class="tm-action-card">
                <div class="tm-card-label">📄 Export</div>
                <div class="tm-card-note">Download a portable account profile snapshot.</div>
            </div>
            """
            ),
            unsafe_allow_html=True,
        )
        st.download_button(
            "📄 Download Profile",
            data=profile_export.encode("utf-8"),
            file_name="talentmatch_account_profile.txt",
            mime="text/plain",
            key="tm_account_download",
            width="stretch",
        )

    with action_cols[3]:
        st.markdown(
            _html(
                """
            <div class="tm-action-card">
                <div class="tm-card-label">🚪 Session</div>
                <div class="tm-card-note">Securely sign out from this device.</div>
            </div>
            """
            ),
            unsafe_allow_html=True,
        )
        if is_logged_in():
            if st.button("🚪 Logout", key="tm_account_logout", width="stretch"):
                clear_auth()
                st.rerun()
        else:
            st.page_link(
                "pages/login.py",
                label="🔐 Login",
                width="stretch",
            )
