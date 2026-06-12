import streamlit as st

from components.footer import render_footer
from components.sidebar import render_sidebar

st.set_page_config(page_title="About Us", page_icon="🏢", layout="wide")

render_sidebar()

st.title("🏢 About Us")
st.caption("TalentMatch Pro – AI-powered CV analysis and ATS optimization platform")

st.markdown("""
# TalentMatch Pro – About Us

TalentMatch Pro is an AI-powered platform built to help job seekers improve their CVs, understand how well they match job descriptions, and prepare stronger job applications.

Our goal is simple: make professional CV analysis, ATS checking, semantic matching, and recruiter-style insights more accessible, faster, and easier to use.

---

## 🚀 Mission

Our mission is to help job seekers increase their interview chances by giving them clear, practical, and AI-powered feedback about their CV.

TalentMatch Pro focuses on:

- CV analysis
- ATS keyword checking
- CV rewriting support
- Semantic job matching
- Recruiter-style evaluation
- Candidate ranking insights
- Downloadable reports

---

## 🎯 Vision

Our vision is to become a practical AI career assistant for modern job seekers and recruiters.

We want TalentMatch Pro to help users understand:

- What is strong in their CV
- What is missing
- Which keywords matter
- How well their CV matches a job description
- What they should improve before applying

---

## 🤖 What We Do

TalentMatch Pro uses AI technology to compare CVs with job descriptions and provide structured feedback.

The platform can help users:

- Identify missing skills and keywords
- Improve ATS compatibility
- Rewrite CV sections
- Compare CVs with job descriptions
- Generate recruiter-ready summaries
- Rank multiple candidates for a role

---

## 🧠 AI-Powered Technology

TalentMatch Pro is built with modern technologies including:

- Python
- FastAPI
- Streamlit
- OpenAI APIs
- Firebase Authentication
- Firebase Storage
- SQL / PostgreSQL-ready architecture
- Render cloud deployment

The system is designed to be simple, fast, and useful for real-world CV and recruitment workflows.

---

## 💼 Who It Is For

TalentMatch Pro is designed for:

- Job seekers
- Students
- Junior developers
- Career changers
- Recruiters
- HR teams
- Small businesses
- Anyone who wants better CV and job matching insights

---

## ⭐ Why TalentMatch Pro

TalentMatch Pro combines CV analysis, ATS checking, semantic matching, and recruiter-style feedback in one place.

Instead of only checking keywords, the platform also looks at meaning, relevance, skills, gaps, and overall job fit.

---

## 📬 Contact

For support, billing questions, refund requests, partnership opportunities, or Pro plan requests, please contact us:

**Email:** dejan.jovic1283@gmail.com
""")