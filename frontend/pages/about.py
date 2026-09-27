import streamlit as st

from components.footer import render_footer
from components.sidebar import render_sidebar


st.set_page_config(page_title="About Us", page_icon="🏢", layout="wide")

render_sidebar()

st.title("🏢 About Us")
st.caption("TalentMatch Pro – AI-powered CV analysis, ATS optimization, and recruiter tools")

st.markdown(
    """
## TalentMatch Pro

**Last Updated: September 2026**

TalentMatch Pro is an AI-powered SaaS platform built to help job seekers, professionals, recruiters, and small teams work with CVs and job descriptions more effectively.

The platform combines structured CV analysis, ATS checking, CV rewriting support, semantic job matching, recruiter-style evaluation, candidate ranking, Candidate Database workflows, saved history, and downloadable reports in one focused workspace.

---

## Mission

Our mission is to give users clear, practical, and structured feedback before they apply for a role or review a candidate.

TalentMatch Pro helps users identify strengths, missing skills, important keywords, relevance gaps, and practical next steps without presenting AI output as a guaranteed hiring decision.

---

## Core Capabilities

- CV analysis and structured recommendations
- ATS keyword and compatibility checking
- CV rewriting assistance
- Semantic matching between CVs and job descriptions
- Recruiter Mode with candidate comparison and ranking
- Candidate Database workflows for recruiter use
- Saved history and downloadable TXT, PDF, and CSV reports

---

## How It Works

Users provide a CV, resume, job description, or candidate information relevant to the selected workflow. TalentMatch Pro processes the submitted information and returns structured analysis, scores, recommendations, summaries, or reports.

AI-generated results should be reviewed by the user and treated as decision-support information rather than as a guarantee of interviews, employment, ATS acceptance, or recruiter approval.

---

## Technology

TalentMatch Pro is built with:

- Python
- FastAPI
- Streamlit
- OpenAI APIs
- Firebase Authentication and Storage
- PostgreSQL
- PayPal recurring billing
- Render cloud deployment

The production architecture is designed for secure authentication, controlled access to paid features, report generation, and reliable CV and recruitment workflows.

---

## Plans and Billing

TalentMatch Pro includes a Free workspace and a Pro plan currently offered for **$19 USD per month** as a recurring subscription billed and managed through **PayPal**.

Current plan details are available on the Pricing page.

---

## Who It Is For

TalentMatch Pro is designed for:

- Job seekers and career changers
- Students and junior professionals
- Recruiters and HR teams
- Small businesses
- Anyone who wants clearer CV and job-matching insights

---

## Contact

For technical support, billing questions, refund requests, partnership opportunities, or general product questions:

**Email:** [support@talentmatchcv.com](mailto:support@talentmatchcv.com)
"""
)

render_footer()
