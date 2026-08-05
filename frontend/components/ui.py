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



THEME_SESSION_KEY = "tm_theme"
SUPPORTED_THEMES = {"system", "light", "dark"}


def _normalize_theme(theme: str | None = None) -> str:
    """Return one supported theme name."""
    value = str(theme or st.session_state.get(THEME_SESSION_KEY, "system")).strip().lower()
    return value if value in SUPPORTED_THEMES else "system"


def _light_theme_css() -> str:
    return """
    :root{color-scheme:light;--tm-control-bg:rgba(255,255,255,.92);--tm-control-text:#0f172a;--tm-control-border:rgba(148,163,184,.34)}
    [data-testid="stMain"] div[data-testid="stPageLink"] a{background:var(--tm-control-bg)!important;border:1px solid var(--tm-control-border)!important;color:var(--tm-control-text)!important}
    [data-testid="stMain"] div[data-testid="stPageLink"] a *{color:inherit!important;-webkit-text-fill-color:currentColor!important}
    """


def _dark_theme_css() -> str:
    return """
    :root{
        color-scheme:dark;
        --tm-navy:#f8fafc;--tm-navy-2:#e2e8f0;--tm-slate:#cbd5e1;--tm-muted:#94a3b8;
        --tm-blue:#60a5fa;--tm-blue-dark:#93c5fd;--tm-green:#34d399;--tm-green-dark:#6ee7b7;
        --tm-purple:#c4b5fd;--tm-amber:#fbbf24;--tm-red:#f87171;
        --tm-card:rgba(15,23,42,.84);--tm-card-strong:rgba(15,23,42,.95);
        --tm-border:rgba(148,163,184,.27);--tm-border-strong:rgba(96,165,250,.54);
        --tm-shadow:0 20px 48px rgba(0,0,0,.30),0 5px 16px rgba(37,99,235,.10);
        --tm-shadow-lg:0 34px 86px rgba(0,0,0,.42),0 12px 32px rgba(37,99,235,.14);
        --tm-blue-soft:rgba(96,165,250,.15);--tm-green-soft:rgba(52,211,153,.14);
        --tm-purple-soft:rgba(196,181,253,.14);--tm-amber-soft:rgba(251,191,36,.14);--tm-red-soft:rgba(248,113,113,.14);
        --tm-control-bg:rgba(15,23,42,.94);--tm-control-text:#f8fafc;--tm-control-border:rgba(148,163,184,.38)
    }
    .stApp{background:radial-gradient(circle at top left,rgba(37,99,235,.18),transparent 31%),radial-gradient(circle at top right,rgba(124,58,237,.13),transparent 29%),radial-gradient(circle at bottom right,rgba(16,185,129,.12),transparent 31%),linear-gradient(180deg,#020617,#0f172a)!important;color:#e2e8f0!important}
    header[data-testid="stHeader"]{background:rgba(2,6,23,.72)!important}
    [data-testid="stMain"] h1,[data-testid="stMain"] h2,[data-testid="stMain"] h3,[data-testid="stMain"] h4,[data-testid="stMain"] h5,[data-testid="stMain"] h6,
    [data-testid="stMain"] label,[data-testid="stMain"] .tm-title,[data-testid="stMain"] .tm-card-title,[data-testid="stMain"] .tm-value,
    [data-testid="stMain"] .tm-section-title,[data-testid="stMain"] .tm-stat-value,[data-testid="stMain"] .tm-score-value,
    [data-testid="stMain"] .tm-pricing-heading,[data-testid="stMain"] .tm-pricing-plan-name,[data-testid="stMain"] .tm-pricing-price,
    [data-testid="stMain"] .tm-pricing-metric-value,[data-testid="stMain"] .tm-pricing-feature-name,[data-testid="stMain"] .tm-pricing-roi-number{color:#f8fafc!important;-webkit-text-fill-color:#f8fafc!important}
    [data-testid="stMain"] p,[data-testid="stMain"] .tm-subtitle,[data-testid="stMain"] .tm-muted,[data-testid="stMain"] .tm-small,
    [data-testid="stMain"] .tm-section-subtitle,[data-testid="stMain"] .tm-stat-label,[data-testid="stMain"] .tm-score-caption,
    [data-testid="stMain"] .tm-pricing-copy,[data-testid="stMain"] .tm-pricing-heading-copy,[data-testid="stMain"] .tm-pricing-price-note,
    [data-testid="stMain"] .tm-pricing-description,[data-testid="stMain"] .tm-pricing-roi-label{color:#cbd5e1!important;-webkit-text-fill-color:#cbd5e1!important}
    [data-testid="stMain"] .tm-kicker,[data-testid="stMain"] .tm-score-label,[data-testid="stMain"] .tm-pricing-label{color:#60a5fa!important;-webkit-text-fill-color:#60a5fa!important}
    [data-testid="stMain"] .tm-hero{border-color:rgba(148,163,184,.28)!important;background:radial-gradient(circle at 7% 9%,rgba(37,99,235,.27),transparent 32%),radial-gradient(circle at 92% 13%,rgba(124,58,237,.20),transparent 30%),radial-gradient(circle at 87% 92%,rgba(16,185,129,.20),transparent 35%),linear-gradient(135deg,rgba(15,23,42,.96),rgba(17,24,39,.94))!important;box-shadow:var(--tm-shadow-lg),inset 0 1px 0 rgba(255,255,255,.055)!important}
    [data-testid="stMain"] .tm-hero:before{background-image:linear-gradient(rgba(255,255,255,.045) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.045) 1px,transparent 1px)!important}
    [data-testid="stMain"] .tm-card,[data-testid="stMain"] .tm-panel,[data-testid="stMain"] .tm-score-card,[data-testid="stMain"] .tm-stat-card,
    [data-testid="stMain"] .tm-alert,[data-testid="stMain"] .tm-empty,[data-testid="stMain"] .tm-report-panel,[data-testid="stMain"] div[data-testid="stMetric"],
    [data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"],[data-testid="stMain"] div[data-testid="stExpander"],
    [data-testid="stMain"] div[data-testid="stDataFrame"],[data-testid="stMain"] div[data-testid="stTable"]{background:rgba(15,23,42,.84)!important;border-color:rgba(148,163,184,.26)!important;color:#e2e8f0!important;box-shadow:var(--tm-shadow)!important}
    [data-testid="stMain"] .tm-card-strong,[data-testid="stMain"] .tm-panel-strong,[data-testid="stMain"] .tm-action-panel{background:radial-gradient(circle at top right,rgba(37,99,235,.16),transparent 35%),radial-gradient(circle at bottom left,rgba(16,185,129,.12),transparent 37%),rgba(15,23,42,.94)!important}
    [data-testid="stMain"] .tm-list-card{background:rgba(15,23,42,.78)!important;border-color:rgba(148,163,184,.25)!important;color:#e2e8f0!important}
    [data-testid="stMain"] .tm-list-card-success{background:rgba(16,185,129,.12)!important;color:#a7f3d0!important}
    [data-testid="stMain"] .tm-list-card-warning{background:rgba(245,158,11,.13)!important;color:#fde68a!important}
    [data-testid="stMain"] .tm-list-card-info{background:rgba(37,99,235,.14)!important;color:#bfdbfe!important}
    [data-testid="stMain"] .tm-check-row,[data-testid="stMain"] .tm-pricing-feature{color:#e2e8f0!important}
    [data-testid="stMain"] .tm-pricing-metric,[data-testid="stMain"] .tm-pricing-plan,[data-testid="stMain"] .tm-pricing-value,
    [data-testid="stMain"] .tm-pricing-workflow,[data-testid="stMain"] .tm-pricing-trust,[data-testid="stMain"] .tm-pricing-faq,
    [data-testid="stMain"] .tm-pricing-contact,[data-testid="stMain"] .tm-pricing-comparison,[data-testid="stMain"] .tm-pricing-roi{background:radial-gradient(circle at top right,rgba(37,99,235,.12),transparent 35%),rgba(15,23,42,.90)!important;border-color:rgba(148,163,184,.27)!important;color:#e2e8f0!important}
    [data-testid="stMain"] .tm-pricing-plan-pro{background:radial-gradient(circle at 92% 8%,rgba(16,185,129,.21),transparent 33%),radial-gradient(circle at 8% 92%,rgba(37,99,235,.18),transparent 37%),rgba(15,23,42,.94)!important;border-color:rgba(52,211,153,.48)!important}
    [data-testid="stMain"] .tm-pricing-feature{background:rgba(30,41,59,.78)!important;border-color:rgba(148,163,184,.22)!important}
    [data-testid="stMain"] .tm-pricing-feature-pro{background:rgba(6,78,59,.30)!important;border-color:rgba(52,211,153,.27)!important;color:#a7f3d0!important}
    [data-testid="stMain"] .tm-pricing-feature-row{color:#cbd5e1!important;border-color:rgba(148,163,184,.20)!important}
    [data-testid="stMain"] .tm-pricing-feature-row:nth-child(even){background:rgba(30,41,59,.55)!important}
    [data-testid="stMain"] div[data-testid="stPageLink"] a{min-height:3rem;background:var(--tm-control-bg)!important;border:1px solid var(--tm-control-border)!important;color:var(--tm-control-text)!important;box-shadow:0 12px 30px rgba(0,0,0,.20)!important}
    [data-testid="stMain"] div[data-testid="stPageLink"] a:hover{background:rgba(30,41,59,.98)!important;border-color:rgba(96,165,250,.60)!important;box-shadow:0 18px 38px rgba(37,99,235,.20)!important}
    [data-testid="stMain"] div[data-testid="stPageLink"] a *{color:#f8fafc!important;-webkit-text-fill-color:#f8fafc!important;opacity:1!important}
    [data-testid="stMain"] .stButton>button,[data-testid="stMain"] .stLinkButton>a,[data-testid="stMain"] div[data-testid="stDownloadButton"] button,
    [data-testid="stMain"] div[data-testid="stFormSubmitButton"] button{background:rgba(15,23,42,.92)!important;border-color:rgba(148,163,184,.36)!important;color:#f8fafc!important}
    [data-testid="stMain"] .stButton>button *,[data-testid="stMain"] .stLinkButton>a *,[data-testid="stMain"] div[data-testid="stDownloadButton"] button *,
    [data-testid="stMain"] div[data-testid="stFormSubmitButton"] button *{color:inherit!important;-webkit-text-fill-color:currentColor!important}
    [data-testid="stMain"] input,[data-testid="stMain"] textarea,[data-testid="stMain"] div[data-baseweb="select"]>div,
    [data-testid="stMain"] div[data-baseweb="select"] div[role="combobox"]{background:rgba(15,23,42,.92)!important;border-color:rgba(148,163,184,.38)!important;color:#f8fafc!important;-webkit-text-fill-color:#f8fafc!important}
    [data-testid="stMain"] div[data-baseweb="select"] span,[data-testid="stMain"] div[data-baseweb="select"] input{color:#f8fafc!important;-webkit-text-fill-color:#f8fafc!important}
    [data-testid="stMain"] div[data-testid="stFileUploader"]{background:radial-gradient(circle at top left,rgba(37,99,235,.15),transparent 40%),rgba(15,23,42,.80)!important;border-color:rgba(96,165,250,.38)!important}
    [data-testid="stMain"] .stTabs [data-baseweb="tab-list"]{background:rgba(15,23,42,.82)!important;border-color:rgba(148,163,184,.26)!important}
    [data-testid="stMain"] .stTabs [data-baseweb="tab"]{color:#cbd5e1!important}
    [data-testid="stMain"] .stTabs [aria-selected="true"]{background:rgba(96,165,250,.16)!important;color:#bfdbfe!important}
    div[data-baseweb="popover"]{color-scheme:dark}
    div[data-baseweb="popover"] ul[role="listbox"],div[data-baseweb="popover"] [role="listbox"]{background:#111827!important;border:1px solid rgba(148,163,184,.32)!important}
    div[data-baseweb="popover"] li[role="option"],div[data-baseweb="popover"] [role="option"]{background:#111827!important;color:#f8fafc!important}
    div[data-baseweb="popover"] li[role="option"]:hover,div[data-baseweb="popover"] [role="option"]:hover,div[data-baseweb="popover"] [aria-selected="true"]{background:#1e3a8a!important;color:#fff!important}
    """


def apply_theme_overrides(theme: str | None = None) -> None:
    """Apply accessible Light, Dark, or system-driven theme overrides."""
    selected = _normalize_theme(theme)
    light_css = _light_theme_css()
    dark_css = _dark_theme_css()
    if selected == "dark":
        css = dark_css
    elif selected == "light":
        css = light_css
    else:
        css = f"{light_css}\\n@media (prefers-color-scheme: dark) {{{dark_css}}}"
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)



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
            --tm-shadow: 0 18px 42px rgba(15, 23, 42, 0.10), 0 4px 12px rgba(37, 99, 235, 0.05);
            --tm-shadow-lg: 0 30px 78px rgba(15, 23, 42, 0.16), 0 10px 28px rgba(37, 99, 235, 0.09);
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

            /* Enterprise layout tokens */
            --tm-page-max: 1240px;
            --tm-page-gutter: clamp(1rem, 2.4vw, 2rem);
            --tm-page-top: clamp(1.25rem, 2.4vw, 2.4rem);
            --tm-page-bottom: clamp(2.5rem, 5vw, 4.5rem);
            --tm-space-1: 0.375rem;
            --tm-space-2: 0.625rem;
            --tm-space-3: 0.875rem;
            --tm-space-4: 1.125rem;
            --tm-space-5: 1.5rem;
            --tm-space-6: 2rem;
            --tm-space-7: 2.75rem;
            --tm-space-8: 3.75rem;
            --tm-section-gap: clamp(2.5rem, 4vw, 4rem);
            --tm-card-gap: clamp(1rem, 1.8vw, 1.5rem);
            --tm-control-gap: 0.75rem;

            /* Canonical 24 / 40 / 64 / 96 px vertical rhythm */
            --tm-rhythm-24: 1.5rem;
            --tm-rhythm-40: 2.5rem;
            --tm-rhythm-64: 4rem;
            --tm-rhythm-96: 6rem;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(37, 99, 235, 0.095), transparent 30%),
                radial-gradient(circle at top right, rgba(124, 58, 237, 0.075), transparent 28%),
                radial-gradient(circle at bottom right, rgba(16, 185, 129, 0.085), transparent 30%),
                linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
        }

        .block-container {
            width: min(100%, var(--tm-page-max));
            max-width: var(--tm-page-max);
            margin-inline: auto;
            padding: var(--tm-page-top) var(--tm-page-gutter) var(--tm-page-bottom);
        }

        /* Global page rhythm: one layout system for every page */
        .block-container > div[data-testid="stVerticalBlock"] {
            gap: var(--tm-card-gap);
        }

        .block-container div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: var(--tm-radius);
        }

        .block-container div[data-testid="stHorizontalBlock"] {
            gap: var(--tm-card-gap);
            align-items: stretch;
        }

        .block-container div[data-testid="column"] {
            min-width: 0;
        }

        .block-container [data-testid="stElementContainer"] {
            margin-bottom: 0;
        }

        .block-container [data-testid="stElementContainer"]:has(> .tm-section-title),
        .block-container [data-testid="stElementContainer"]:has(> .tm-pricing-heading) {
            margin-top: var(--tm-section-gap);
        }

        .block-container [data-testid="stForm"] {
            padding: clamp(1rem, 2vw, 1.5rem);
            border: 1px solid var(--tm-border);
            border-radius: var(--tm-radius);
            background: rgba(255,255,255,0.72);
            box-shadow: var(--tm-shadow);
        }

        .block-container [data-testid="stForm"] > div {
            gap: var(--tm-control-gap);
        }

        .block-container hr {
            margin: var(--tm-space-7) 0;
            border-color: rgba(148,163,184,0.24);
        }

        .tm-page-shell {
            width: 100%;
            max-width: var(--tm-page-max);
            margin-inline: auto;
        }

        .tm-section {
            margin-top: var(--tm-section-gap);
        }

        .tm-section:first-child {
            margin-top: 0;
        }

        .tm-grid {
            display: grid;
            gap: var(--tm-card-gap);
        }

        .tm-grid-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .tm-grid-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
        .tm-grid-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }

        .tm-stack {
            display: flex;
            flex-direction: column;
            gap: var(--tm-card-gap);
        }

        .tm-cluster {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: var(--tm-control-gap);
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
            box-shadow: var(--tm-shadow-lg), inset 0 1px 0 rgba(255,255,255,0.82);
            margin-bottom: 1.45rem;
            transform: translateZ(0);
            transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease;
        }

        .tm-hero:hover {
            transform: translateY(-2px);
            border-color: rgba(37, 99, 235, 0.30);
            box-shadow: 0 38px 96px rgba(15, 23, 42, 0.18), 0 16px 34px rgba(37, 99, 235, 0.12), inset 0 1px 0 rgba(255,255,255,0.90);
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



        /* Shared enterprise spacing for cards, panels and page intros */
        .tm-hero,
        .tm-card,
        .tm-panel,
        .tm-action-panel,
        .tm-report-panel,
        .tm-score-card,
        .tm-stat-card,
        .tm-empty {
            margin-block: 0;
        }

        .tm-hero {
            margin-bottom: clamp(1.4rem, 2.6vw, 2.15rem);
        }

        .tm-section-title {
            margin-top: var(--tm-section-gap);
            margin-bottom: var(--tm-space-3);
        }

        .tm-section-subtitle {
            margin-top: calc(var(--tm-space-2) * -1);
            margin-bottom: var(--tm-space-5);
            max-width: 820px;
        }

        .tm-card, .tm-panel, .tm-action-panel, .tm-report-panel, .tm-score-card, .tm-stat-card {
            height: 100%;
        }

        /* -----------------------------------------------------------------
           Pricing page — unified enterprise premium components
           ----------------------------------------------------------------- */
        .tm-pricing-metric,
        .tm-pricing-plan,
        .tm-pricing-value,
        .tm-pricing-workflow,
        .tm-pricing-trust,
        .tm-pricing-faq,
        .tm-pricing-contact {
            position: relative;
            border: 1px solid rgba(148, 163, 184, 0.28);
            background: linear-gradient(145deg, rgba(255,255,255,0.96), rgba(248,250,252,0.84));
            box-shadow: 0 20px 44px rgba(15,23,42,0.11), 0 6px 16px rgba(37,99,235,0.055), inset 0 1px 0 rgba(255,255,255,0.88);
            backdrop-filter: blur(16px);
            transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease;
        }

        .tm-pricing-metric:hover,
        .tm-pricing-plan:hover,
        .tm-pricing-value:hover,
        .tm-pricing-workflow:hover,
        .tm-pricing-trust:hover,
        .tm-pricing-faq:hover,
        .tm-pricing-contact:hover {
            transform: translateY(-2px);
            border-color: rgba(37,99,235,0.34);
            box-shadow: 0 30px 66px rgba(15,23,42,0.15), 0 12px 26px rgba(37,99,235,0.09), inset 0 1px 0 rgba(255,255,255,0.94);
        }

        .tm-pricing-grid {
            display: grid;
            gap: var(--tm-card-gap);
            align-items: stretch;
            width: 100%;
        }
        .tm-pricing-grid-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .tm-pricing-grid-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
        .tm-pricing-grid-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
        .tm-pricing-grid > * { min-width: 0; height: 100%; }

        .tm-pricing-metric { min-height: 150px; padding: 1.2rem; border-radius: 24px; }
        .tm-pricing-label { color: var(--tm-blue); font-size: .72rem; font-weight: 950; letter-spacing: .11em; text-transform: uppercase; margin-bottom: .55rem; }
        .tm-pricing-metric-value { color: var(--tm-navy); font-size: 1.55rem; line-height: 1.1; font-weight: 950; letter-spacing: -.04em; margin-bottom: .45rem; }
        .tm-pricing-copy { color: var(--tm-slate); line-height: 1.58; font-size: .94rem; }
        .tm-pricing-heading { margin: 2.75rem 0 1rem; color: var(--tm-navy); font-size: clamp(1.7rem,2vw,2.2rem); font-weight: 950; letter-spacing: -.045em; }
        .tm-pricing-heading-copy { margin: -.55rem 0 1.2rem; max-width: 780px; color: var(--tm-slate); line-height: 1.65; }

        .tm-pricing-plan { min-height: 590px; padding: 1.85rem; border-radius: 32px; overflow: hidden; }
        .tm-pricing-plan-pro {
            border-color: rgba(16,185,129,.52);
            background: radial-gradient(circle at 92% 8%, rgba(16,185,129,.23), transparent 32%), radial-gradient(circle at 8% 92%, rgba(37,99,235,.15), transparent 36%), linear-gradient(145deg, rgba(255,255,255,.98), rgba(240,253,250,.88));
            box-shadow: 0 34px 82px rgba(16,185,129,.19), 0 14px 30px rgba(37,99,235,.11), inset 0 1px 0 rgba(255,255,255,.94);
        }
        .tm-pricing-plan-pro:hover { border-color: rgba(16,185,129,.70); box-shadow: 0 44px 104px rgba(16,185,129,.24), 0 20px 42px rgba(37,99,235,.15), inset 0 1px 0 rgba(255,255,255,.98); }
        .tm-pricing-ribbon { display:inline-flex; align-items:center; gap:.35rem; padding:.42rem .8rem; border-radius:999px; background:rgba(16,185,129,.14); color:#047857; border:1px solid rgba(16,185,129,.26); font-size:.74rem; font-weight:950; letter-spacing:.08em; text-transform:uppercase; margin-bottom:1rem; box-shadow:0 8px 18px rgba(16,185,129,.08); }
        .tm-pricing-plan-name { color:var(--tm-navy); font-size:1.48rem; font-weight:950; letter-spacing:-.03em; }
        .tm-pricing-price { color:var(--tm-navy); font-size:4.25rem; line-height:.95; letter-spacing:-.08em; font-weight:950; margin:.75rem 0 .35rem; }
        .tm-pricing-price span { color:var(--tm-slate); font-size:1rem; letter-spacing:0; font-weight:850; }
        .tm-pricing-price-note { color:var(--tm-slate); font-size:.87rem; margin-bottom:1.15rem; }
        .tm-pricing-description { color:#475569; line-height:1.62; min-height:78px; margin-bottom:1rem; }
        .tm-pricing-feature-list { display:grid; gap:.58rem; margin-top:1rem; }
        .tm-pricing-feature { display:flex; align-items:flex-start; gap:.62rem; padding:.72rem .78rem; border-radius:16px; border:1px solid rgba(148,163,184,.18); background:rgba(248,250,252,.78); color:#334155; line-height:1.4; font-weight:760; box-shadow:0 7px 16px rgba(15,23,42,.035); }
        .tm-pricing-feature-pro { border-color:rgba(16,185,129,.22); background:rgba(236,253,245,.78); }
        .tm-pricing-feature-icon { flex:0 0 auto; width:1.35rem; text-align:center; }

        .tm-pricing-roi { padding:1.45rem; border-radius:28px; border:1px solid rgba(37,99,235,.30); background:radial-gradient(circle at top left,rgba(37,99,235,.17),transparent 36%),radial-gradient(circle at bottom right,rgba(16,185,129,.15),transparent 38%),rgba(255,255,255,.92); box-shadow:0 28px 68px rgba(37,99,235,.13),0 8px 20px rgba(15,23,42,.07),inset 0 1px 0 rgba(255,255,255,.9); }
        .tm-pricing-roi-number { color:var(--tm-navy); font-size:2.3rem; font-weight:950; letter-spacing:-.06em; line-height:1; margin-bottom:.35rem; }
        .tm-pricing-roi-label { color:var(--tm-slate); font-size:.88rem; line-height:1.5; }

        .tm-pricing-comparison { overflow:hidden; border-radius:28px; border:1px solid rgba(148,163,184,.30); background:rgba(255,255,255,.92); box-shadow:0 28px 68px rgba(15,23,42,.13),0 8px 20px rgba(37,99,235,.07),inset 0 1px 0 rgba(255,255,255,.9); transition:transform 220ms ease,box-shadow 220ms ease,border-color 220ms ease; }
        .tm-pricing-comparison:hover { transform:translateY(-2px); border-color:rgba(37,99,235,.34); box-shadow:0 38px 88px rgba(15,23,42,.17),0 14px 30px rgba(37,99,235,.10),inset 0 1px 0 rgba(255,255,255,.95); }
        .tm-pricing-feature-row { display:grid; grid-template-columns:minmax(180px,1.7fr) minmax(90px,.65fr) minmax(90px,.65fr); align-items:center; gap:1rem; padding:.94rem 1rem; border-bottom:1px solid rgba(148,163,184,.18); color:#475569; font-size:.94rem; }
        .tm-pricing-feature-row:last-child{border-bottom:0}.tm-pricing-feature-row:nth-child(even){background:rgba(248,250,252,.72)}
        .tm-pricing-feature-header{color:#f8fafc;background:linear-gradient(135deg,#0f172a,#1e293b)!important;font-weight:950}.tm-pricing-feature-name{color:var(--tm-navy);font-weight:900}.tm-pricing-feature-pro{color:#047857;font-weight:950}

        .tm-pricing-secure { padding:1.5rem; border-radius:28px; background:radial-gradient(circle at top right,rgba(37,99,235,.27),transparent 36%),linear-gradient(135deg,rgba(15,23,42,.98),rgba(30,41,59,.96)); border:1px solid rgba(148,163,184,.28); box-shadow:0 32px 76px rgba(15,23,42,.24),0 10px 24px rgba(37,99,235,.12); }
        .tm-pricing-secure-title{color:#f8fafc;font-size:1.35rem;font-weight:950;letter-spacing:-.025em;margin-bottom:.45rem}.tm-pricing-secure-copy{color:#cbd5e1;line-height:1.65}
        .tm-pricing-value,.tm-pricing-trust{padding:1.2rem;border-radius:24px;min-height:170px}.tm-pricing-workflow{padding:1.4rem;border-radius:26px;min-height:195px}.tm-pricing-faq{padding:1.08rem 1.18rem;border-radius:20px;margin-bottom:.82rem}.tm-pricing-contact{padding:1.3rem 1.4rem;border-radius:24px}
        .tm-pricing-icon{font-size:1.38rem;margin-bottom:.55rem}.tm-pricing-card-title{color:var(--tm-navy);font-size:1.06rem;font-weight:950;letter-spacing:-.02em;margin-bottom:.45rem}.tm-pricing-workflow-text{color:#1e293b;font-size:1.03rem;font-weight:760;line-height:1.65;margin-bottom:1rem}.tm-pricing-workflow-meta{color:var(--tm-slate);font-size:.84rem;line-height:1.5}.tm-pricing-faq-question{color:var(--tm-navy);font-weight:950;margin-bottom:.25rem}

        .tm-pricing-cta { position:relative; overflow:hidden; padding:1.9rem; border-radius:32px; border:1px solid rgba(16,185,129,.44); background:radial-gradient(circle at top right,rgba(16,185,129,.25),transparent 34%),radial-gradient(circle at bottom left,rgba(37,99,235,.19),transparent 38%),rgba(255,255,255,.96); box-shadow:0 38px 94px rgba(16,185,129,.20),0 16px 38px rgba(37,99,235,.13),inset 0 1px 0 rgba(255,255,255,.94); margin-top:1rem; transition:transform 240ms ease,box-shadow 240ms ease,border-color 240ms ease; }
        .tm-pricing-cta:hover{transform:translateY(-2px);border-color:rgba(16,185,129,.64);box-shadow:0 48px 116px rgba(16,185,129,.25),0 22px 48px rgba(37,99,235,.17),0 0 46px rgba(16,185,129,.09),inset 0 1px 0 rgba(255,255,255,.98)}
        .tm-pricing-cta-title{color:var(--tm-navy);font-size:clamp(1.85rem,3vw,2.7rem);font-weight:950;letter-spacing:-.06em;line-height:1.03;margin-bottom:.6rem}.tm-pricing-cta-price{color:#047857;font-size:1.2rem;font-weight:950;margin-bottom:.55rem}.tm-pricing-cta-copy{color:var(--tm-slate);line-height:1.65;max-width:760px}

        @media (prefers-reduced-motion: reduce) {
            .tm-hero,.tm-pricing-metric,.tm-pricing-plan,.tm-pricing-value,.tm-pricing-workflow,.tm-pricing-trust,.tm-pricing-faq,.tm-pricing-contact,.tm-pricing-comparison,.tm-pricing-cta { transition:none!important; }
            .tm-hero:hover,.tm-pricing-metric:hover,.tm-pricing-plan:hover,.tm-pricing-value:hover,.tm-pricing-workflow:hover,.tm-pricing-trust:hover,.tm-pricing-faq:hover,.tm-pricing-contact:hover,.tm-pricing-comparison:hover,.tm-pricing-cta:hover { transform:none!important; }
        }

        /* Keep cards visually grounded: depth without excessive movement. */
        .tm-pricing-metric, .tm-pricing-plan, .tm-pricing-value,
        .tm-pricing-workflow, .tm-pricing-trust, .tm-pricing-faq,
        .tm-pricing-contact, .tm-pricing-comparison, .tm-pricing-cta {
            will-change: box-shadow, border-color;
        }

        @media (max-width: 980px) {
            .tm-pricing-grid-4 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .tm-pricing-grid-3 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }

        @media (max-width: 720px) {
            .tm-pricing-grid-2, .tm-pricing-grid-3, .tm-pricing-grid-4 { grid-template-columns: 1fr; }
            .tm-pricing-feature-row { grid-template-columns:1.4fr .7fr .7fr; gap:.55rem; padding:.82rem .72rem; font-size:.82rem; }
            .tm-pricing-plan { min-height:auto; }
        }

        @media (max-width: 980px) {
            .tm-grid-4 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .tm-grid-3 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }

        @media (max-width: 760px) {
            .block-container {
                width: 100%;
                padding: 1rem 0.9rem 2.5rem;
            }
            .block-container div[data-testid="stHorizontalBlock"] { gap: 0.8rem; }
            .tm-grid-2, .tm-grid-3, .tm-grid-4 { grid-template-columns: 1fr; }
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
    apply_theme_overrides()


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
