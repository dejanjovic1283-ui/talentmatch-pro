# 🚀 TalentMatch Pro

<div align="center">

# TalentMatch Pro

### AI-Powered Resume Intelligence & Recruitment Platform

Analyze resumes, optimize ATS performance, perform semantic candidate matching, generate recruiter-ready reports, and accelerate hiring decisions with Artificial Intelligence.

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green.svg)]()
[![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-red.svg)]()
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue.svg)]()
[![Firebase](https://img.shields.io/badge/Firebase-Authentication-orange.svg)]()
[![Paddle](https://img.shields.io/badge/Paddle-Billing-purple.svg)]()
[![Render](https://img.shields.io/badge/Render-Deployment-black.svg)]()

</div>

---

# 🌐 Live Demo

Frontend:
https://talentmatch-frontend-dejan.onrender.com

Backend API:
https://talentmatch-backend-1283.onrender.com

Repository:
https://github.com/dejanjovic1283-ui/talentmatch-pro

---

# 📌 Overview

TalentMatch Pro is a production-ready AI SaaS platform that helps job seekers and recruiters make smarter hiring decisions.

The platform combines:
- AI Resume Analysis
- ATS Optimization
- Semantic Matching
- Recruiter Tools
- PDF Reporting
- Firebase Authentication
- Paddle Billing

---

# ✨ Features

## 📄 AI Resume Analysis

- PDF upload
- AI-powered evaluation
- Match scoring
- Strength analysis
- Missing skill detection
- Recommendations

## 🎯 ATS Checker

- ATS keyword extraction
- Missing keyword detection
- ATS readiness scoring
- Optimization suggestions

## 🧠 Semantic Matching (Pro)

- Resume vs Job Description comparison
- Semantic similarity scoring
- AI relevance ranking

## 👔 Recruiter Mode (Pro)

- Candidate ranking
- Candidate comparison
- Hiring workflow optimization

## ✍️ AI CV Rewrite (Pro)

- ATS-friendly rewriting
- Professional wording suggestions
- Resume enhancement

## 📄 PDF Reports (Pro)

- Downloadable PDF reports
- Summary
- Recommendations
- ATS insights

---

# 💳 Plans

## Free

- Limited analyses
- ATS Checker
- Basic recommendations

## Pro ($9/month)

- Unlimited analyses
- Semantic Matching
- Recruiter Mode
- AI CV Rewrite
- PDF Reports
- Priority features

---

# 🏗 Architecture

```text
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
 └── Paddle Billing
```

---

# 🛠 Technology Stack

## Backend

- FastAPI
- SQLAlchemy
- PostgreSQL
- OpenAI API
- Firebase Admin SDK
- Paddle Billing
- ReportLab

## Frontend

- Streamlit
- Pandas
- Plotly
- Requests

## Infrastructure

- Docker
- Render
- GitHub

---

# 📁 Project Structure

```text
backend/
frontend/
docker-compose.yml
Dockerfile.backend
Dockerfile.frontend
README.md
```

---

# 🔌 API Endpoints

## Analysis

POST /analyze-resume

POST /analyze-test

## ATS

POST /ats-test

POST /ats-check

## Semantic Matching

POST /semantic-match

## Recruiter

POST /recruiter/rank-candidates

## CV Rewrite

POST /rewrite-cv

## Reports

POST /reports/analysis-pdf

## User

GET /me

GET /history

## Billing

POST /billing/create-checkout

POST /billing/create-portal

POST /billing/webhook

---

# 🔥 Firebase

Used for:

- Authentication
- User management
- Storage
- Resume uploads

Storage example:

users/{user_id}/cvs/{timestamp}_{filename}.pdf

---

# 💳 Paddle Billing

Supported events:

- transaction.completed
- subscription.created
- subscription.activated
- subscription.updated
- subscription.canceled
- subscription.past_due

Webhook:

POST /billing/webhook

---

# ⚙ Environment Variables

## Backend

OPENAI_API_KEY

DATABASE_URL

FIREBASE_PROJECT_ID

FIREBASE_STORAGE_BUCKET

FIREBASE_CREDENTIALS

PADDLE_API_KEY

PADDLE_WEBHOOK_SECRET

## Frontend

BACKEND_URL

---

# 🐳 Docker

Build:

docker compose up --build

Frontend:

http://localhost:8501

Backend:

http://localhost:8000

---

# 🚀 Render Deployment Guide

## Backend

1. Create Web Service
2. Connect GitHub repository
3. Root Directory: backend
4. Build Command:

pip install -r requirements.txt

5. Start Command:

uvicorn main:app --host 0.0.0.0 --port $PORT

## Frontend

1. Create Web Service
2. Root Directory: frontend
3. Build Command:

pip install -r requirements.txt

4. Start Command:

streamlit run app.py --server.port $PORT --server.address 0.0.0.0

---

# 📸 Screenshots

Add screenshots here:

screenshots/home.png

screenshots/analysis.png

screenshots/ats.png

screenshots/recruiter.png

screenshots/pricing.png

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

- Enterprise plans
- Team accounts
- Organization workspaces
- Interview preparation
- Hiring analytics
- Multi-language support
- Candidate benchmarking

---

# 👨‍💻 Author

Dejan Jović

GitHub:
https://github.com/dejanjovic1283-ui

Repository:
https://github.com/dejanjovic1283-ui/talentmatch-pro

Email:
dejan.jovic1283@gmail.com

---

# 📜 License

MIT License

---

TalentMatch Pro — AI-Powered Hiring Intelligence.
