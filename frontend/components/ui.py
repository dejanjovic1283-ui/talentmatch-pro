"""Shared UI helpers and design system for TalentMatch Pro frontend pages.

This module is intentionally self-contained and backwards compatible with older
pages that already import: apply_global_styles, render_hero, card,
get_display_name, get_initials, get_user_email and safe_html.
"""

from __future__ import annotations

import re
from html import escape
from typing import Any, Iterable, Sequence

import streamlit as st


# -----------------------------------------------------------------------------
# User helpers
# -----------------------------------------------------------------------------


def get_user_email() -> str:
    """Return the best available user email from Streamlit session state."""
    user = st.session_state.get("user")
    profile = st.session_state.get("profile")

    user_email = user.get("email", "") if isinstance(user, dict) else ""
    profile_email = profile.get("email", "") if isinstance(profile, dict) else ""

    return str(
        st.session_state.get("email")
        or st.session_state.get("user_email")
        or user_email
        or profile_email
        or ""
    ).strip()



def _split_compact_name(value: str) -> str:
    """Convert compact names like DejanJovic1283 into Dejan Jovic."""
    text = str(value or "").strip()
    if not text:
        return ""

    text = re.sub(r"[0-9]+", "", text)
    text = text.replace(".", " ").replace("_", " ").replace("-", " ")
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    parts = [part for part in text.split() if part]
    if not parts:
        return ""

    return " ".join(part[:1].upper() + part[1:].lower() for part in parts[:3])



def _clean_display_name(value: Any) -> str:
    """Return a clean, human-friendly display name for the UI."""
    text = str(value or "").strip()
    if not text:
        return ""

    if "@" in text:
        text = text.split("@", 1)[0]

    cleaned = _split_compact_name(text)
    if cleaned:
        compact = re.sub(r"[^a-zA-Z]", "", cleaned).lower()
        if "dejan" in compact and "jovic" in compact:
            return "Dejan Jovic"
        return cleaned

    return ""



def get_display_name(default: str = "TalentMatch User") -> str:
    """Return one consistent friendly display name across all frontend pages."""
    priority_values: list[Any] = []

    profile = st.session_state.get("profile")
    if isinstance(profile, dict):
        priority_values.extend(
            profile.get(key) for key in ("full_name", "display_name", "name")
        )

    user = st.session_state.get("user")
    if isinstance(user, dict):
        priority_values.extend(
            user.get(key) for key in ("full_name", "display_name", "name")
        )

    priority_values.extend(
        st.session_state.get(key) for key in ("full_name", "display_name", "name")
    )

    for value in priority_values:
        display_name = _clean_display_name(value)
        if display_name:
            return display_name

    email_name = _clean_display_name(get_user_email())
    if email_name:
        return email_name

    return default



def get_initials(name: str | None = None) -> str:
    """Return two-letter initials for avatars."""
    base = name or get_display_name()
    parts = [part for part in base.replace("_", " ").split() if part]
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[1][0]}".upper()
    return (base[:2] or "TM").upper()



def safe_html(value: Any) -> str:
    """Escape text before injecting it into custom HTML blocks."""
    return escape(str(value or ""), quote=True)



def _safe_percent(value: int | float) -> int:
    try:
        numeric = int(float(value))
    except Exception:
        numeric = 0
    return max(0, min(100, numeric))


# -----------------------------------------------------------------------------
# Global design system
# -----------------------------------------------------------------------------


def apply_global_styles() -> None:
    """Apply the TalentMatch Pro design system to the active Streamlit page."""
    st.markdown(
        """
        <style>
        :root {
            --tm-navy: #0f172a;
            --tm-navy-2: #111827;
            --tm-slate: #64748b;
            --tm-muted: #94a3b8;
            --tm-blue: #2563eb;
            --tm-blue-dark: #1d4ed8;
            --tm-green: #10b981;
            --tm-green-dark: #047857;
            --tm-purple: #7c3aed;
            --tm-amber: #f59e0b;
            --tm-red: #dc2626;
            --tm-card: rgba(255, 255, 255, 0.80);
            --tm-card-strong: rgba(255, 255, 255, 0.94);
            --tm-border: rgba(148, 163, 184, 0.24);
            --tm-border-strong: rgba(37, 99, 235, 0.35);
            --tm-shadow: 0 18px 48px rgba(15, 23, 42, 0.06);
            --tm-shadow-lg: 0 28px 85px rgba(15, 23, 42, 0.11);
            --tm-radius-sm: 14px;
            --tm-radius-md: 20px;
            --tm-radius: 24px;
            --tm-radius-lg: 32px;
            --tm-radius-xl: 38px;
            --tm-blue-soft: rgba(37, 99, 235, 0.10);
            --tm-green-soft: rgba(16, 185, 129, 0.10);
            --tm-purple-soft: rgba(124, 58, 237, 0.10);
            --tm-amber-soft: rgba(245, 158, 11, 0.12);
            --tm-red-soft: rgba(220, 38, 38, 0.10);
            --tm-focus: 0 0 0 4px rgba(37, 99, 235, 0.16);
            --tm-transition: 160ms ease;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(37, 99, 235, 0.095), transparent 30%),
                radial-gradient(circle at top right, rgba(124, 58, 237, 0.075), transparent 28%),
                radial-gradient(circle at bottom right, rgba(16, 185, 129, 0.085), transparent 30%),
                linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
        }

        .block-container {
            max-width: 1220px;
            padding-top: 2.35rem;
            padding-bottom: 3.2rem;
        }

        h1, h2, h3 {
            letter-spacing: -0.035em;
            color: var(--tm-navy);
        }

        footer { visibility: hidden; }
        #MainMenu { visibility: hidden; }
        header[data-testid="stHeader"] { background: rgba(248, 250, 252, 0.45); }

        .tm-hero {
            position: relative;
            overflow: hidden;
            padding: 2.35rem;
            border-radius: var(--tm-radius-lg);
            border: 1px solid var(--tm-border);
            background:
                radial-gradient(circle at 6% 10%, rgba(37, 99, 235, 0.20), transparent 30%),
                radial-gradient(circle at 92% 15%, rgba(124, 58, 237, 0.14), transparent 29%),
                radial-gradient(circle at 88% 92%, rgba(16, 185, 129, 0.17), transparent 34%),
                linear-gradient(135deg, rgba(255,255,255,0.90), rgba(248,250,252,0.96));
            box-shadow: var(--tm-shadow-lg);
            margin-bottom: 1.45rem;
        }

        .tm-hero:before {
            content: "";
            position: absolute;
            inset: 0;
            background-image:
                linear-gradient(rgba(15,23,42,0.035) 1px, transparent 1px),
                linear-gradient(90deg, rgba(15,23,42,0.035) 1px, transparent 1px);
            background-size: 34px 34px;
            mask-image: linear-gradient(90deg, rgba(0,0,0,0.18), transparent 72%);
            pointer-events: none;
        }

        .tm-hero-grid {
            position: relative;
            z-index: 1;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1.6rem;
        }

        .tm-kicker {
            color: var(--tm-blue);
            font-size: 0.78rem;
            font-weight: 950;
            text-transform: uppercase;
            letter-spacing: 0.13em;
            margin-bottom: 0.45rem;
        }

        .tm-title {
            font-size: clamp(2.15rem, 4vw, 3.25rem);
            line-height: 1.03;
            font-weight: 950;
            color: var(--tm-navy);
            letter-spacing: -0.058em;
            margin-bottom: 0.7rem;
        }

        .tm-subtitle {
            font-size: 1.12rem;
            color: var(--tm-slate);
            line-height: 1.58;
            max-width: 850px;
        }

        .tm-avatar-xl {
            position: relative;
            min-width: 116px;
            width: 116px;
            height: 116px;
            border-radius: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 2.18rem;
            font-weight: 950;
            letter-spacing: -0.055em;
            background: linear-gradient(135deg, #2563eb, #10b981);
            border: 1px solid rgba(255,255,255,0.72);
            box-shadow: 0 24px 58px rgba(37, 99, 235, 0.28);
        }

        .tm-avatar-xl.tm-avatar-round {
            border-radius: 999px;
        }

        .tm-avatar-badge {
            position: absolute;
            right: -7px;
            bottom: 8px;
            padding: 0.24rem 0.52rem;
            border-radius: 999px;
            background: #0f172a;
            color: white;
            font-size: 0.68rem;
            font-weight: 950;
            letter-spacing: 0.06em;
            border: 2px solid white;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.22);
        }

        .tm-card {
            padding: 1.35rem;
            border-radius: var(--tm-radius);
            border: 1px solid var(--tm-border);
            background: var(--tm-card);
            box-shadow: var(--tm-shadow);
            min-height: 100%;
            backdrop-filter: blur(14px);
        }

        .tm-card:hover {
            border-color: var(--tm-border-strong);
            transform: translateY(-1px);
            transition: 0.18s ease;
        }

        .tm-card-strong {
            background: var(--tm-card-strong);
            box-shadow: var(--tm-shadow-lg);
        }

        .tm-card-title {
            font-size: 1.18rem;
            font-weight: 900;
            color: var(--tm-navy);
            margin-bottom: 0.45rem;
            letter-spacing: -0.025em;
        }

        .tm-muted {
            color: var(--tm-slate);
            font-size: 0.95rem;
            line-height: 1.5;
        }

        .tm-value {
            color: var(--tm-navy);
            font-size: 1.75rem;
            font-weight: 950;
            letter-spacing: -0.045em;
        }

        .tm-small {
            color: var(--tm-muted);
            font-size: 0.84rem;
            line-height: 1.35;
        }

        .tm-section-title {
            margin: 2rem 0 0.8rem 0;
            font-size: 1.6rem;
            font-weight: 950;
            color: var(--tm-navy);
            letter-spacing: -0.04em;
        }

        .tm-section-subtitle {
            margin-top: -0.45rem;
            margin-bottom: 0.95rem;
            color: var(--tm-slate);
            font-size: 0.98rem;
        }

        .tm-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            margin: 0.25rem 0.25rem 0.25rem 0;
            padding: 0.42rem 0.72rem;
            border-radius: 999px;
            background: rgba(37, 99, 235, 0.09);
            color: #1d4ed8;
            font-size: 0.85rem;
            font-weight: 850;
            border: 1px solid rgba(37, 99, 235, 0.13);
        }

        .tm-pill-green {
            background: rgba(16,185,129,0.10);
            color: #047857;
            border-color: rgba(16,185,129,0.18);
        }

        .tm-pill-amber {
            background: rgba(245,158,11,0.12);
            color: #b45309;
            border-color: rgba(245,158,11,0.22);
        }

        .tm-pill-red {
            background: rgba(220,38,38,0.10);
            color: #b91c1c;
            border-color: rgba(220,38,38,0.18);
        }

        .tm-pill-dark {
            background: rgba(15,23,42,0.92);
            color: white;
            border-color: rgba(15,23,42,0.12);
        }

        .tm-progress-track {
            width: 100%;
            height: 12px;
            border-radius: 999px;
            background: rgba(148, 163, 184, 0.20);
            overflow: hidden;
            border: 1px solid rgba(148, 163, 184, 0.16);
        }

        .tm-progress-fill {
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, #2563eb, #10b981);
            box-shadow: 0 8px 24px rgba(37, 99, 235, 0.22);
        }

        .tm-stat-card {
            padding: 1.25rem;
            border-radius: 24px;
            border: 1px solid rgba(148,163,184,0.22);
            background: rgba(255,255,255,0.78);
            box-shadow: 0 14px 38px rgba(15,23,42,0.052);
        }

        .tm-stat-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
            margin-bottom: 0.65rem;
        }

        .tm-stat-icon {
            width: 42px;
            height: 42px;
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(37,99,235,0.10);
            font-size: 1.25rem;
        }

        .tm-stat-label {
            color: var(--tm-slate);
            font-size: 0.86rem;
            font-weight: 800;
        }

        .tm-stat-value {
            color: var(--tm-navy);
            font-size: 2rem;
            font-weight: 950;
            letter-spacing: -0.055em;
            line-height: 1;
        }

        .tm-stat-delta {
            color: var(--tm-green-dark);
            font-size: 0.82rem;
            font-weight: 850;
            margin-top: 0.4rem;
        }

        .tm-alert {
            padding: 1rem 1.1rem;
            border-radius: 20px;
            border: 1px solid rgba(148,163,184,0.22);
            background: rgba(255,255,255,0.76);
            box-shadow: 0 12px 32px rgba(15,23,42,0.045);
            margin: 0.65rem 0;
        }

        .tm-alert-info { border-color: rgba(37,99,235,0.22); background: rgba(37,99,235,0.07); }
        .tm-alert-success { border-color: rgba(16,185,129,0.24); background: rgba(16,185,129,0.08); }
        .tm-alert-warning { border-color: rgba(245,158,11,0.26); background: rgba(245,158,11,0.10); }
        .tm-alert-danger { border-color: rgba(220,38,38,0.22); background: rgba(220,38,38,0.08); }

        .tm-check-row {
            display: flex;
            align-items: center;
            gap: 0.55rem;
            padding: 0.48rem 0;
            color: var(--tm-navy);
            font-weight: 750;
        }

        .tm-check-dot {
            width: 22px;
            height: 22px;
            border-radius: 999px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: rgba(16,185,129,0.13);
            color: #047857;
            font-size: 0.78rem;
            font-weight: 950;
            flex: 0 0 auto;
        }

        .tm-empty {
            text-align: center;
            padding: 2.2rem 1.5rem;
            border-radius: 28px;
            border: 1px dashed rgba(148,163,184,0.42);
            background: rgba(255,255,255,0.62);
        }

        .tm-empty-icon { font-size: 2.9rem; margin-bottom: 0.35rem; }

        div[data-testid="stMetric"] {
            background: rgba(255,255,255,0.70);
            border: 1px solid rgba(148,163,184,0.22);
            padding: 1rem;
            border-radius: 22px;
            box-shadow: 0 12px 30px rgba(15,23,42,0.04);
        }

        .stButton > button,
        .stLinkButton > a,
        div[data-testid="stDownloadButton"] button,
        div[data-testid="stFormSubmitButton"] button {
            min-height: 3rem;
            border-radius: var(--tm-radius-sm) !important;
            padding: 0.72rem 1rem !important;
            font-weight: 900 !important;
            letter-spacing: -0.012em !important;
            border: 1px solid rgba(148,163,184,0.30) !important;
            background: rgba(255,255,255,0.90) !important;
            color: var(--tm-navy) !important;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.055) !important;
            transition: transform var(--tm-transition), box-shadow var(--tm-transition), border-color var(--tm-transition), background var(--tm-transition) !important;
        }

        .stButton > button:hover,
        .stLinkButton > a:hover,
        div[data-testid="stDownloadButton"] button:hover,
        div[data-testid="stFormSubmitButton"] button:hover {
            transform: translateY(-1px);
            border-color: rgba(37,99,235,0.40) !important;
            box-shadow: 0 16px 34px rgba(37,99,235,0.12) !important;
        }

        .stButton > button[kind="primary"],
        div[data-testid="stFormSubmitButton"] button[kind="primary"] {
            border-color: transparent !important;
            background: linear-gradient(135deg, var(--tm-blue), var(--tm-blue-dark)) !important;
            color: #ffffff !important;
            box-shadow: 0 16px 34px rgba(37,99,235,0.24) !important;
        }

        .stButton > button[kind="primary"]:hover,
        div[data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
            background: linear-gradient(135deg, #1d4ed8, #1e40af) !important;
            box-shadow: 0 20px 42px rgba(37,99,235,0.30) !important;
        }

        .stButton > button:disabled,
        div[data-testid="stDownloadButton"] button:disabled,
        div[data-testid="stFormSubmitButton"] button:disabled {
            opacity: 0.52 !important;
            cursor: not-allowed !important;
            transform: none !important;
            box-shadow: none !important;
        }

        .stTextInput input, .stTextArea textarea, .stNumberInput input, .stDateInput input,
        .stSelectbox div[data-baseweb="select"] > div,
        .stMultiSelect div[data-baseweb="select"] > div {
            border-radius: var(--tm-radius-sm) !important;
            border-color: rgba(148,163,184,0.30) !important;
            background: rgba(255,255,255,0.78) !important;
        }

        div[data-testid="stFileUploader"] {
            border: 1px dashed rgba(37,99,235,0.35);
            border-radius: var(--tm-radius);
            padding: 0.75rem;
            background: radial-gradient(circle at top left, rgba(37,99,235,0.08), transparent 38%), rgba(255,255,255,0.66);
        }

        div[data-testid="stExpander"], div[data-testid="stDataFrame"], div[data-testid="stTable"] {
            border: 1px solid var(--tm-border) !important;
            border-radius: var(--tm-radius-md) !important;
            background: rgba(255,255,255,0.76) !important;
            box-shadow: var(--tm-shadow);
            overflow: hidden;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.45rem;
            border-radius: 999px;
            padding: 0.35rem;
            background: rgba(255,255,255,0.68);
            border: 1px solid var(--tm-border);
        }

        .stTabs [data-baseweb="tab"] { border-radius: 999px; padding: 0.6rem 1rem; font-weight: 850; }
        .stTabs [aria-selected="true"] { background: var(--tm-blue-soft); color: var(--tm-blue-dark); }

        .tm-panel { padding: 1.35rem; border-radius: var(--tm-radius); border: 1px solid var(--tm-border); background: rgba(255,255,255,0.76); box-shadow: var(--tm-shadow); backdrop-filter: blur(14px); }
        .tm-panel-strong { background: rgba(255,255,255,0.94); box-shadow: var(--tm-shadow-lg); }
        .tm-action-panel { position: relative; overflow: hidden; padding: 1.45rem; border-radius: var(--tm-radius); border: 1px solid rgba(37,99,235,0.24); background: radial-gradient(circle at top right, rgba(37,99,235,0.12), transparent 34%), radial-gradient(circle at bottom left, rgba(16,185,129,0.10), transparent 36%), rgba(255,255,255,0.90); box-shadow: var(--tm-shadow-lg); }
        .tm-action-content { position: relative; z-index: 1; }
        .tm-score-card { padding: 1.35rem; min-height: 178px; border-radius: var(--tm-radius); border: 1px solid var(--tm-border); background: rgba(255,255,255,0.84); box-shadow: var(--tm-shadow); }
        .tm-score-card-blue { border-top: 4px solid var(--tm-blue); }
        .tm-score-card-green { border-top: 4px solid var(--tm-green); }
        .tm-score-card-purple { border-top: 4px solid var(--tm-purple); }
        .tm-score-card-amber { border-top: 4px solid var(--tm-amber); }
        .tm-score-card-red { border-top: 4px solid var(--tm-red); }
        .tm-score-label { color: var(--tm-blue); font-size: 0.76rem; font-weight: 950; text-transform: uppercase; letter-spacing: 0.13em; line-height: 1.45; }
        .tm-score-value { margin-top: 0.72rem; color: var(--tm-navy); font-size: clamp(2rem, 3.6vw, 2.7rem); font-weight: 950; line-height: 1; letter-spacing: -0.06em; }
        .tm-score-caption { margin-top: 0.65rem; color: var(--tm-slate); font-size: 0.96rem; line-height: 1.45; }
        .tm-report-panel { padding: 1.35rem; border-radius: var(--tm-radius); border: 1px solid var(--tm-border); background: linear-gradient(135deg, rgba(255,255,255,0.92), rgba(248,250,252,0.82)); box-shadow: var(--tm-shadow); }
        .tm-list-card { padding: 0.95rem 1rem; border-radius: 18px; border: 1px solid var(--tm-border); background: rgba(255,255,255,0.70); margin-bottom: 0.7rem; color: var(--tm-navy); line-height: 1.5; }
        .tm-list-card-success { background: rgba(16,185,129,0.08); border-color: rgba(16,185,129,0.20); color: var(--tm-green-dark); }
        .tm-list-card-warning { background: rgba(245,158,11,0.10); border-color: rgba(245,158,11,0.22); color: #a16207; }
        .tm-list-card-info { background: rgba(37,99,235,0.08); border-color: rgba(37,99,235,0.18); color: #0369a1; }
        .tm-divider { height: 1px; margin: 1.6rem 0; background: linear-gradient(90deg, transparent, rgba(148,163,184,0.46), transparent); }

        @media (max-width: 760px) {
            .block-container { padding-top: 1.25rem; }
            .tm-hero { padding: 1.45rem; border-radius: 26px; }
            .tm-hero-grid { flex-direction: column; align-items: flex-start; }
            .tm-avatar-xl { width: 92px; height: 92px; min-width: 92px; border-radius: 28px; }
            .tm-title { font-size: 2.1rem; }
            .tm-card { padding: 1.05rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# Rendering helpers / components
# -----------------------------------------------------------------------------


def render_hero(kicker: str, title: str, subtitle: str, initials: str | None = None) -> None:
    """Render the standard TalentMatch page hero."""
    avatar = get_initials() if initials is None else initials
    st.markdown(
        f"""
        <div class="tm-hero">
            <div class="tm-hero-grid">
                <div>
                    <div class="tm-kicker">{safe_html(kicker)}</div>
                    <div class="tm-title">{safe_html(title)}</div>
                    <div class="tm-subtitle">{safe_html(subtitle)}</div>
                </div>
                <div class="tm-avatar-xl">{safe_html(avatar)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_premium_hero(
    *,
    kicker: str,
    title: str,
    subtitle: str,
    initials: str | None = None,
    badge: str | None = None,
    footer: str | None = None,
) -> None:
    """Render an enhanced hero with avatar badge support."""
    avatar = get_initials() if initials is None else initials
    badge_html = f'<div class="tm-avatar-badge">{safe_html(badge)}</div>' if badge else ""
    footer_html = f'<div style="margin-top:.8rem"><span class="tm-pill tm-pill-dark">{safe_html(footer)}</span></div>' if footer else ""
    st.markdown(
        f"""
        <div class="tm-hero">
            <div class="tm-hero-grid">
                <div>
                    <div class="tm-kicker">{safe_html(kicker)}</div>
                    <div class="tm-title">{safe_html(title)}</div>
                    <div class="tm-subtitle">{safe_html(subtitle)}</div>
                    {footer_html}
                </div>
                <div class="tm-avatar-xl tm-avatar-round">{safe_html(avatar)}{badge_html}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def card(title: str, body: str, icon: str = "✨") -> None:
    """Render a simple content card. Body may contain safe project-controlled HTML."""
    st.markdown(
        f"""
        <div class="tm-card">
            <div class="tm-card-title">{safe_html(icon)} {safe_html(title)}</div>
            <div class="tm-muted">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_card(title: str, body: str, icon: str = "✨", strong: bool = False) -> None:
    """Render a card with optional stronger elevation."""
    class_name = "tm-card tm-card-strong" if strong else "tm-card"
    st.markdown(
        f"""
        <div class="{class_name}">
            <div class="tm-card-title">{safe_html(icon)} {safe_html(title)}</div>
            <div class="tm-muted">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_section_title(title: str, subtitle: str | None = None) -> None:
    """Render a standardized section title."""
    subtitle_html = f'<div class="tm-section-subtitle">{safe_html(subtitle)}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="tm-section-title">{safe_html(title)}</div>
        {subtitle_html}
        """,
        unsafe_allow_html=True,
    )



def render_kpi_card(label: str, value: Any, icon: str = "📊", delta: str | None = None) -> None:
    """Render a dashboard/account KPI card."""
    delta_html = f'<div class="tm-stat-delta">{safe_html(delta)}</div>' if delta else ""
    st.markdown(
        f"""
        <div class="tm-stat-card">
            <div class="tm-stat-top">
                <div>
                    <div class="tm-stat-label">{safe_html(label)}</div>
                    <div class="tm-stat-value">{safe_html(value)}</div>
                </div>
                <div class="tm-stat-icon">{safe_html(icon)}</div>
            </div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_status_pill(label: str, status: str = "active") -> str:
    """Return HTML for a status pill. Useful inside custom cards."""
    normalized = status.lower().strip()
    class_name = "tm-pill"
    icon = "🔵"
    if normalized in {"active", "online", "success", "pro", "healthy"}:
        class_name = "tm-pill tm-pill-green"
        icon = "🟢"
    elif normalized in {"warning", "trial", "degraded"}:
        class_name = "tm-pill tm-pill-amber"
        icon = "🟡"
    elif normalized in {"danger", "error", "offline", "expired"}:
        class_name = "tm-pill tm-pill-red"
        icon = "🔴"
    elif normalized in {"dark", "vip"}:
        class_name = "tm-pill tm-pill-dark"
        icon = "💎"
    return f'<span class="{class_name}">{icon} {safe_html(label)}</span>'



def render_progress_card(
    title: str,
    value: int | float,
    total: int | float,
    subtitle: str = "Monthly usage",
    icon: str = "📊",
) -> None:
    """Render a premium progress card."""
    try:
        percent = _safe_percent((float(value) / float(total)) * 100 if float(total) else 0)
    except Exception:
        percent = 0
    st.markdown(
        f"""
        <div class="tm-card tm-card-strong">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;margin-bottom:.85rem">
                <div>
                    <div class="tm-card-title">{safe_html(icon)} {safe_html(title)}</div>
                    <div class="tm-muted">{safe_html(subtitle)}</div>
                </div>
                <div class="tm-value">{percent}%</div>
            </div>
            <div class="tm-progress-track"><div class="tm-progress-fill" style="width:{percent}%"></div></div>
            <div class="tm-small" style="margin-top:.7rem">{safe_html(value)} / {safe_html(total)} used</div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_alert(message: str, title: str | None = None, kind: str = "info", icon: str | None = None) -> None:
    """Render a custom alert card."""
    normalized = kind.lower().strip()
    if normalized not in {"info", "success", "warning", "danger"}:
        normalized = "info"
    icon_value = icon or {"info": "ℹ️", "success": "✅", "warning": "⚠️", "danger": "🚨"}[normalized]
    title_html = f'<div class="tm-card-title" style="margin-bottom:.25rem">{safe_html(icon_value)} {safe_html(title)}</div>' if title else ""
    st.markdown(
        f"""
        <div class="tm-alert tm-alert-{normalized}">
            {title_html}
            <div class="tm-muted">{safe_html(message)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_checklist(items: Iterable[str]) -> None:
    """Render a verified checklist inside the current layout."""
    rows = "".join(
        f'<div class="tm-check-row"><span class="tm-check-dot">✓</span><span>{safe_html(item)}</span></div>'
        for item in items
    )
    st.markdown(rows, unsafe_allow_html=True)



def render_empty_state(
    title: str,
    message: str,
    icon: str = "📭",
) -> None:
    """Render a premium empty state block."""
    st.markdown(
        f"""
        <div class="tm-empty">
            <div class="tm-empty-icon">{safe_html(icon)}</div>
            <div class="tm-card-title">{safe_html(title)}</div>
            <div class="tm-muted">{safe_html(message)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_membership_card(
    *,
    plan: str,
    billing: str = "PayPal",
    status: str = "Active",
    renewal: str = "Not available",
    usage: str = "0 / 0",
    pro_enabled: bool = False,
) -> None:
    """Render a premium membership/subscription card."""
    badge = "💎 PRO MEMBER" if pro_enabled else "🌱 FREE MEMBER"
    status_kind = "active" if status.lower() in {"active", "online", "enabled"} else "warning"
    st.markdown(
        f"""
        <div class="tm-card tm-card-strong">
            <div class="tm-kicker">Membership</div>
            <div class="tm-card-title" style="font-size:1.45rem">{safe_html(badge)}</div>
            <div style="margin:.5rem 0 .8rem 0">{render_status_pill(status, status_kind)}</div>
            <div class="tm-muted">Billing</div>
            <div style="font-weight:900;color:#0f172a;margin-bottom:.55rem">{safe_html(billing)}</div>
            <div class="tm-muted">Current plan</div>
            <div style="font-weight:900;color:#0f172a;margin-bottom:.55rem">{safe_html(plan)}</div>
            <div class="tm-muted">Renewal</div>
            <div style="font-weight:900;color:#0f172a;margin-bottom:.55rem">{safe_html(renewal)}</div>
            <div class="tm-muted">Usage</div>
            <div style="font-weight:900;color:#0f172a">{safe_html(usage)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_feature_grid(items: Sequence[tuple[str, str, str]]) -> None:
    """Render a responsive-ish feature list using Streamlit columns.

    Each item is: (icon, title, description).
    """
    if not items:
        return
    columns = st.columns(min(3, len(items)))
    for index, (icon, title, description) in enumerate(items):
        with columns[index % len(columns)]:
            render_card(title=title, body=safe_html(description), icon=icon)

# -----------------------------------------------------------------------------
# PROFI-EXTRA shared components
# -----------------------------------------------------------------------------


def _score_tone(value: int | float) -> tuple[str, str]:
    percent = _safe_percent(value)
    if percent >= 80:
        return "green", "Excellent"
    if percent >= 65:
        return "blue", "Strong"
    if percent >= 50:
        return "purple", "Competitive"
    if percent >= 35:
        return "amber", "Needs improvement"
    return "red", "Low match"


def render_action_panel(*, title: str, description: str, icon: str = "🚀", eyebrow: str = "AI WORKFLOW") -> None:
    st.markdown(
        f"""
        <div class="tm-action-panel"><div class="tm-action-content">
            <div class="tm-kicker">{safe_html(eyebrow)}</div>
            <div class="tm-card-title" style="font-size:1.42rem">{safe_html(icon)} {safe_html(title)}</div>
            <div class="tm-muted">{safe_html(description)}</div>
        </div></div>
        """,
        unsafe_allow_html=True,
    )


def render_score_card(*, label: str, value: int | float | str, caption: str | None = None, tone: str | None = None, suffix: str = "/100") -> None:
    try:
        numeric_value: int | None = _safe_percent(float(value))
    except (TypeError, ValueError):
        numeric_value = None
    allowed = {"blue", "green", "purple", "amber", "red"}
    normalized_tone = (tone or "").strip().lower()
    if normalized_tone not in allowed:
        normalized_tone = _score_tone(numeric_value or 0)[0] if numeric_value is not None else "blue"
    displayed = f"{numeric_value}{suffix}" if numeric_value is not None else safe_html(value)
    final_caption = caption if caption is not None else (_score_tone(numeric_value or 0)[1] if numeric_value is not None else "")
    st.markdown(
        f"""
        <div class="tm-score-card tm-score-card-{normalized_tone}">
            <div class="tm-score-label">{safe_html(label)}</div>
            <div class="tm-score-value">{displayed}</div>
            <div class="tm-score-caption">{safe_html(final_caption)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_report_panel(*, title: str = "Download reports", description: str = "Export professional TalentMatch Pro results for review, sharing, and record keeping.", icon: str = "📥") -> None:
    st.markdown(
        f"""
        <div class="tm-report-panel">
            <div class="tm-kicker">REPORT CENTER</div>
            <div class="tm-card-title">{safe_html(icon)} {safe_html(title)}</div>
            <div class="tm-muted">{safe_html(description)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_list_cards(items: Iterable[str], *, kind: str = "info", empty_message: str = "No items available.") -> None:
    values = [str(item).strip() for item in items if str(item).strip()]
    if not values:
        st.markdown(f'<div class="tm-small">{safe_html(empty_message)}</div>', unsafe_allow_html=True)
        return
    class_name = {
        "success": "tm-list-card tm-list-card-success",
        "warning": "tm-list-card tm-list-card-warning",
        "info": "tm-list-card tm-list-card-info",
    }.get(kind.strip().lower(), "tm-list-card")
    st.markdown(
        "".join(f'<div class="{class_name}">{safe_html(item)}</div>' for item in values),
        unsafe_allow_html=True,
    )


def render_divider() -> None:
    st.markdown('<div class="tm-divider"></div>', unsafe_allow_html=True)


def render_page_intro(*, kicker: str, title: str, subtitle: str, icon: str = "✨", badge: str | None = None) -> None:
    badge_html = f'<span class="tm-pill tm-pill-dark">{safe_html(badge)}</span>' if badge else ""
    st.markdown(
        f"""
        <div class="tm-hero"><div class="tm-hero-grid">
            <div>
                <div class="tm-kicker">{safe_html(kicker)}</div>
                <div class="tm-title">{safe_html(title)}</div>
                <div class="tm-subtitle">{safe_html(subtitle)}</div>
                <div style="margin-top:.9rem">{badge_html}</div>
            </div>
            <div class="tm-avatar-xl">{safe_html(icon)}</div>
        </div></div>
        """,
        unsafe_allow_html=True,
    )

