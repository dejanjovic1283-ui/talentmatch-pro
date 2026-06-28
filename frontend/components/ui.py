"""Shared UI helpers for TalentMatch Pro frontend pages."""

from __future__ import annotations

import re
from html import escape
from typing import Any

import streamlit as st


def get_user_email() -> str:
    return (
        st.session_state.get("email")
        or st.session_state.get("user_email")
        or st.session_state.get("user", {}).get("email", "")
        or st.session_state.get("profile", {}).get("email", "")
        or ""
    )


def get_display_name(default: str = "Dejan Jovic") -> str:
    for key in ("display_name", "name", "full_name"):
        value = st.session_state.get(key)
        if value:
            return str(value).strip()

    for source in (st.session_state.get("user", {}), st.session_state.get("profile", {})):
        if isinstance(source, dict):
            for key in ("display_name", "name", "full_name"):
                value = source.get(key)
                if value:
                    return str(value).strip()

    email = get_user_email()
    if email:
        local = email.split("@")[0]
        compact = re.sub(r"[^a-zA-Z]", "", local).lower()
        if "dejan" in compact and "jovic" in compact:
            return "Dejan Jovic"
        clean = re.sub(r"[0-9]+", "", local)
        clean = clean.replace(".", " ").replace("_", " ").replace("-", " ")
        parsed = " ".join(part.capitalize() for part in clean.split() if part)
        return parsed or default

    return default


def get_initials(name: str | None = None) -> str:
    base = name or get_display_name()
    parts = [part for part in base.replace("_", " ").split() if part]
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[1][0]}".upper()
    return (base[:2] or "TM").upper()


def safe_html(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def apply_global_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --tm-navy: #0f172a;
            --tm-slate: #64748b;
            --tm-blue: #2563eb;
            --tm-green: #10b981;
            --tm-card: rgba(255, 255, 255, 0.78);
            --tm-border: rgba(148, 163, 184, 0.24);
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(37, 99, 235, 0.08), transparent 30%),
                radial-gradient(circle at bottom right, rgba(16, 185, 129, 0.08), transparent 30%),
                linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
        }

        .block-container {
            max-width: 1220px;
            padding-top: 2.4rem;
            padding-bottom: 3rem;
        }

        h1, h2, h3 {
            letter-spacing: -0.035em;
            color: var(--tm-navy);
        }

        footer { visibility: hidden; }

        .tm-hero {
            padding: 2.25rem;
            border-radius: 32px;
            border: 1px solid var(--tm-border);
            background:
                radial-gradient(circle at top left, rgba(37, 99, 235, 0.18), transparent 34%),
                radial-gradient(circle at bottom right, rgba(16, 185, 129, 0.16), transparent 38%),
                linear-gradient(135deg, rgba(255,255,255,0.88), rgba(248,250,252,0.94));
            box-shadow: 0 24px 70px rgba(15, 23, 42, 0.08);
            margin-bottom: 1.4rem;
        }

        .tm-hero-grid {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1.5rem;
        }

        .tm-kicker {
            color: var(--tm-blue);
            font-size: 0.78rem;
            font-weight: 950;
            text-transform: uppercase;
            letter-spacing: 0.13em;
            margin-bottom: 0.4rem;
        }

        .tm-title {
            font-size: 3.05rem;
            line-height: 1.03;
            font-weight: 950;
            color: var(--tm-navy);
            letter-spacing: -0.055em;
            margin-bottom: 0.65rem;
        }

        .tm-subtitle {
            font-size: 1.12rem;
            color: var(--tm-slate);
            line-height: 1.58;
            max-width: 850px;
        }

        .tm-avatar-xl {
            min-width: 112px;
            width: 112px;
            height: 112px;
            border-radius: 34px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 2.15rem;
            font-weight: 950;
            background: linear-gradient(135deg, #2563eb, #10b981);
            box-shadow: 0 24px 55px rgba(37, 99, 235, 0.26);
        }

        .tm-card {
            padding: 1.35rem;
            border-radius: 24px;
            border: 1px solid var(--tm-border);
            background: var(--tm-card);
            box-shadow: 0 18px 48px rgba(15, 23, 42, 0.055);
            min-height: 100%;
        }

        .tm-card:hover {
            border-color: rgba(37, 99, 235, 0.42);
            transform: translateY(-1px);
            transition: 0.18s ease;
        }

        .tm-card-title {
            font-size: 1.18rem;
            font-weight: 900;
            color: var(--tm-navy);
            margin-bottom: 0.45rem;
        }

        .tm-muted {
            color: var(--tm-slate);
            font-size: 0.95rem;
            line-height: 1.48;
        }

        .tm-value {
            color: var(--tm-navy);
            font-size: 1.7rem;
            font-weight: 950;
            letter-spacing: -0.04em;
        }

        .tm-pill {
            display: inline-block;
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

        .tm-section-title {
            margin: 2rem 0 0.8rem 0;
            font-size: 1.6rem;
            font-weight: 950;
            color: var(--tm-navy);
            letter-spacing: -0.04em;
        }

        div[data-testid="stMetric"] {
            background: rgba(255,255,255,0.68);
            border: 1px solid rgba(148,163,184,0.22);
            padding: 1rem;
            border-radius: 22px;
        }

        .stButton > button, .stLinkButton > a {
            border-radius: 14px !important;
            font-weight: 850 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(kicker: str, title: str, subtitle: str, initials: str | None = None) -> None:
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


def card(title: str, body: str, icon: str = "✨") -> None:
    st.markdown(
        f"""
        <div class="tm-card">
            <div class="tm-card-title">{safe_html(icon)} {safe_html(title)}</div>
            <div class="tm-muted">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
