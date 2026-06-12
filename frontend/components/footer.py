import streamlit as st
from datetime import datetime


def render_footer() -> None:
    """Render a professional footer for TalentMatch Pro pages."""

    year = datetime.now().year

    st.divider()

    st.markdown(
        f"""
        <style>
            .tmp-footer {{
                margin-top: 2.5rem;
                padding: 1.5rem 0 0.5rem 0;
                color: rgba(49, 51, 63, 0.72);
                font-size: 0.92rem;
                line-height: 1.6;
            }}
            .tmp-footer-title {{
                font-weight: 800;
                color: rgba(49, 51, 63, 0.92);
                font-size: 1.02rem;
                margin-bottom: 0.25rem;
            }}
            .tmp-footer-grid {{
                display: grid;
                grid-template-columns: 1.3fr 1fr 1fr;
                gap: 1.5rem;
                align-items: start;
            }}
            .tmp-footer-small {{
                margin-top: 1.25rem;
                padding-top: 0.9rem;
                border-top: 1px solid rgba(49, 51, 63, 0.12);
                font-size: 0.84rem;
                color: rgba(49, 51, 63, 0.58);
            }}
            .tmp-footer a {{
                color: inherit;
                text-decoration: none;
            }}
            .tmp-footer a:hover {{
                text-decoration: underline;
            }}
            @media (max-width: 900px) {{
                .tmp-footer-grid {{
                    grid-template-columns: 1fr;
                    gap: 0.9rem;
                }}
            }}
        </style>

        <div class="tmp-footer">
            <div class="tmp-footer-grid">
                <div>
                    <div class="tmp-footer-title">🎯 TalentMatch Pro</div>
                    <div>AI-powered CV analysis, ATS optimization, semantic job matching, and recruiter-ready insights.</div>
                </div>
                <div>
                    <div class="tmp-footer-title">📬 Contact</div>
                    <div>Email: <a href="mailto:dejan.jovic1283@gmail.com">dejan.jovic1283@gmail.com</a></div>
                    <div>Country: Serbia</div>
                </div>
                <div>
                    <div class="tmp-footer-title">🔐 Legal</div>
                    <div>Terms • Privacy • Refund</div>
                    <div>Built for job seekers and recruiters.</div>
                </div>
            </div>
            <div class="tmp-footer-small">
                © {year} TalentMatch Pro. All rights reserved. AI-generated outputs should be reviewed before use.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )