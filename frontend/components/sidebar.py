import streamlit as st

from auth_utils import clear_auth, is_logged_in, is_pro_user, refresh_profile
from components.ui import get_display_name, get_initials, safe_html


def _sidebar_css() -> None:
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #111827 48%, #020617 100%);
            border-right: 1px solid rgba(148, 163, 184, 0.18);
        }

        section[data-testid="stSidebar"] * { color: #e5e7eb; }
        section[data-testid="stSidebar"] hr { border-color: rgba(148,163,184,0.25); }
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #cbd5e1; }
        section[data-testid="stSidebar"] a {
            border-radius: 14px;
            padding: 0.18rem 0.35rem;
            font-weight: 750;
        }
        section[data-testid="stSidebar"] a:hover {
            background: rgba(37, 99, 235, 0.16);
        }

        .tm-side-brand {
            padding: 1rem 0.9rem 0.95rem 0.9rem;
            border: 1px solid rgba(148,163,184,0.22);
            border-radius: 24px;
            background:
                radial-gradient(circle at top left, rgba(37,99,235,0.24), transparent 42%),
                rgba(15,23,42,0.86);
            box-shadow: 0 18px 45px rgba(0,0,0,0.25);
            margin: 0.35rem 0 1rem 0;
        }

        .tm-side-logo-row {
            display: flex;
            align-items: center;
            gap: 0.72rem;
            margin-bottom: 0.55rem;
        }

        .tm-side-logo {
            width: 50px;
            height: 50px;
            border-radius: 17px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.7rem;
            background: linear-gradient(135deg, #2563eb, #10b981);
            box-shadow: 0 14px 34px rgba(37,99,235,0.34);
        }

        .tm-side-title { font-size: 1.25rem; font-weight: 950; letter-spacing: -0.03em; color: #f8fafc !important; }
        .tm-side-subtitle { color: #94a3b8 !important; font-size: 0.82rem; line-height: 1.38; }

        .tm-side-user {
            padding: 0.95rem;
            border-radius: 22px;
            background: linear-gradient(135deg, rgba(37,99,235,0.24), rgba(16,185,129,0.16));
            border: 1px solid rgba(148,163,184,0.24);
            margin: 0.35rem 0 0.95rem 0;
        }

        .tm-side-avatar {
            width: 52px;
            height: 52px;
            border-radius: 18px;
            background: linear-gradient(135deg, #60a5fa, #34d399);
            color: white !important;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 950;
            font-size: 1.06rem;
            float: left;
            margin-right: 0.75rem;
            box-shadow: 0 14px 30px rgba(16,185,129,0.24);
        }

        .tm-side-welcome { font-weight: 950; color: #f8fafc !important; line-height: 1.16; }
        .tm-side-plan {
            display: inline-block;
            margin-top: 0.35rem;
            padding: 0.16rem 0.56rem;
            border-radius: 999px;
            background: rgba(255,255,255,0.12);
            color: #bfdbfe !important;
            font-size: 0.72rem;
            font-weight: 900;
            letter-spacing: 0.03em;
        }

        .tm-side-section {
            color: #94a3b8 !important;
            font-size: 0.72rem;
            font-weight: 950;
            letter-spacing: 0.105em;
            text-transform: uppercase;
            margin: 1rem 0 0.36rem 0;
        }

        .tm-side-footer {
            margin-top: 0.9rem;
            padding: 0.86rem;
            border-radius: 18px;
            background: rgba(15, 23, 42, 0.64);
            border: 1px solid rgba(148, 163, 184, 0.17);
            color: #94a3b8 !important;
            font-size: 0.77rem;
            line-height: 1.38;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar():
    with st.sidebar:
        _sidebar_css()

        st.markdown(
            """
            <div class="tm-side-brand">
                <div class="tm-side-logo-row">
                    <div class="tm-side-logo">🎯</div>
                    <div>
                        <div class="tm-side-title">TalentMatch Pro</div>
                        <div class="tm-side-subtitle">Premium AI CV workspace</div>
                    </div>
                </div>
                <div class="tm-side-subtitle">ATS optimization • semantic matching • recruiter reports</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if is_logged_in():
            name = get_display_name()
            initials = get_initials(name)
            plan = "PRO" if is_pro_user() else "FREE"
            st.markdown(
                f"""
                <div class="tm-side-user">
                    <div class="tm-side-avatar">{safe_html(initials)}</div>
                    <div class="tm-side-welcome">Welcome:<br>{safe_html(name)}</div>
                    <span class="tm-side-plan">{safe_html(plan)} ACCOUNT</span>
                    <div style="clear:both;"></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="tm-side-user">
                    <div class="tm-side-avatar">TM</div>
                    <div class="tm-side-welcome">Welcome:<br>Guest</div>
                    <span class="tm-side-plan">SIGN IN</span>
                    <div style="clear:both;"></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown('<div class="tm-side-section">Workspace</div>', unsafe_allow_html=True)
        st.page_link("app.py", label="🏠 Dashboard")
        st.page_link("pages/cv_analysis.py", label="📄 CV Analysis")
        st.page_link("pages/ats_checker.py", label="📋 ATS Checker")
        st.page_link("pages/cv_rewrite.py", label="✍ CV Rewrite")

        st.markdown('<div class="tm-side-section">Pro tools</div>', unsafe_allow_html=True)
        if is_pro_user():
            st.page_link("pages/semantic_match.py", label="🧠 Semantic Match")
            st.page_link("pages/recruiter_mode.py", label="👥 Recruiter Mode")
        else:
            st.page_link("pages/pricing.py", label="🧠 Semantic Match 🔒")
            st.page_link("pages/pricing.py", label="👥 Recruiter Mode 🔒")

        st.markdown('<div class="tm-side-section">Account</div>', unsafe_allow_html=True)
        st.page_link("pages/history.py", label="📜 History")
        st.page_link("pages/pricing.py", label="💳 Pricing")
        st.page_link("pages/account.py", label="⚙ Account")

        st.markdown('<div class="tm-side-section">Company</div>', unsafe_allow_html=True)
        st.page_link("pages/about.py", label="ℹ About Us")
        st.page_link("pages/contact.py", label="📬 Contact Us")
        st.page_link("pages/terms.py", label="📃 Terms")
        st.page_link("pages/privacy.py", label="🔒 Privacy")
        st.page_link("pages/refund.py", label="💸 Refund")

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

        st.markdown(
            """
            <div class="tm-side-footer">
                <b>Production polish</b><br>
                Consistent SaaS UI, PayPal billing, PDF reports and ATS tools.
            </div>
            """,
            unsafe_allow_html=True,
        )
