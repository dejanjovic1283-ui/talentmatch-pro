# 🚀 TalentMatch Pro


# TalentMatch Pro

### AI-Powered Resume Intelligence & Recruitment Platform

Analyze resumes, optimize ATS performance, perform semantic candidate matching, generate recruiter-ready reports, and accelerate hiring decisions with Artificial Intelligence.

![Python](https://img.shields.io/badge/Python-3.13-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi)
![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-FF4B4B?style=for-the-badge&logo=streamlit)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-336791?style=for-the-badge&logo=postgresql)
![Firebase](https://img.shields.io/badge/Firebase-Authentication-FFCA28?style=for-the-badge&logo=firebase)
![PayPal](https://img.shields.io/badge/PayPal-Billing-00457C?style=for-the-badge&logo=paypal)
![Render](https://img.shields.io/badge/Render-Deployment-black?style=for-the-badge)


---

# 🌍 Live Demo

Frontend:
https://talentmatch-frontend-dejan.onrender.com

Backend:
https://talentmatch-backend-1283.onrender.com

---

# 📌 Overview

TalentMatch Pro is a production-ready AI SaaS platform for job seekers, recruiters and hiring teams.

## Core Modules

- AI Resume Analysis
- ATS Optimization
- Semantic Matching
- Recruiter Mode
- AI CV Rewrite
- PDF Reporting
- Firebase Authentication
- PayPal Billing

---

# ✨ Features

## 📄 AI Resume Analysis
- Resume scoring
- Skill gap detection
- Improvement recommendations
- Recruiter insights

## 🎯 ATS Checker
- ATS readiness score
- Keyword extraction
- Missing keyword detection

## 🧠 Semantic Matching
- Resume vs Job Description
- Similarity scoring
- AI-powered relevance ranking

## 👔 Recruiter Mode
- Candidate ranking
- Candidate comparison
- Hiring recommendations

## ✍️ AI CV Rewrite
- ATS-friendly optimization
- Professional wording improvements

## 📄 PDF Reports
- Downloadable recruiter reports
- Analysis summaries
- ATS insights

---

# 💳 Plans

## Free
- Limited analyses
- ATS Checker
- Basic recommendations

## Pro
- Unlimited analyses
- Semantic Matching
- Recruiter Mode
- AI CV Rewrite
- PDF Reports

---

# 🏗 Architecture

User
 │
 ▼
Streamlit Frontend
 │
 ▼
FastAPI Backend
 │
 ├── OpenAI API
 ├── Firebase Auth
 ├── Firebase Storage
 ├── PostgreSQL
 └── PayPal Billing
```

---

# 🛠 Technology Stack

## Backend
- FastAPI
- SQLAlchemy
- PostgreSQL
- OpenAI API
- Firebase Admin SDK
- ReportLab

## Frontend
- Streamlit
- Pandas
- Plotly

## Infrastructure
- Docker
- Render
- GitHub

---

# 📁 Project Structure

backend/
frontend/
Dockerfile.backend
Dockerfile.frontend
README.md

---

# 🔌 API Endpoints

### Analysis
POST /analyze-resume

### ATS
POST /ats-check

### Semantic Matching
POST /semantic-match

### Recruiter
POST /recruiter/rank-candidates

### User
GET /me

### Billing
POST /billing/create-checkout
POST /billing/create-portal
POST /billing/webhook

---

# 🔥 Firebase

Used for:
- Authentication
- User management
- Resume storage

---

# 💳 PayPal Billing

Supported:
- Monthly subscriptions
- Checkout
- Customer Portal
- Webhooks

---

# 🐳 Docker

docker compose up --build

---

# 🚀 Deployment

## Backend

uvicorn main:app --host 0.0.0.0 --port $PORT

## Frontend

streamlit run app.py --server.port $PORT --server.address 0.0.0.0

---

# 🔒 Security

Never commit:

.env
serviceAccountKey.json
frontend/.streamlit/secrets.toml
*.db
.venv/

---

# 📈 Roadmap

- Enterprise Plans
- Team Accounts
- Hiring Analytics
- Candidate Benchmarking
- AI Interview Preparation

---

# 👨‍💻 Founder & Developer

Dejan Jović

GitHub:
https://github.com/dejanjovic1283-ui

LinkedIn:
https://www.linkedin.com/in/dejan-jović-5babb538a

---

# ⭐ TalentMatch Pro

AI-Powered Hiring Intelligence.
