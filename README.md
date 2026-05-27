# 🚀 TalentMatch Pro

AI-powered SaaS platform for CV analysis, ATS optimization, semantic candidate matching, recruiter workflows, and AI hiring automation.

## ✨ Features

### CV Analysis
- PDF CV upload
- AI resume analysis
- Match score generation
- Strengths and weaknesses detection
- Improvement recommendations

### ATS Checker
- ATS keyword matching
- Missing keyword detection
- Resume optimization insights

### Semantic Matching
- Embedding-based matching
- Candidate ranking
- Job description similarity scoring

### Recruiter Mode
- Recruiter workflow tools
- Candidate overview
- Hiring optimization

### Billing
- Stripe integration
- Pro subscriptions
- Usage limits

### Authentication
- Firebase Authentication
- Firebase Storage
- Secure file handling

---

## 🏗 Tech Stack

Backend:
- FastAPI
- SQLAlchemy
- SQLite / PostgreSQL
- OpenAI API
- Firebase
- Stripe

Frontend:
- Streamlit
- Python

Infrastructure:
- Render
- Docker
- GitHub

---

## 📁 Project Structure

```text
talentmatch-pro/

backend/
├── auth.py
├── db.py
├── firebase.py
├── main.py
├── models.py
├── openai_service.py
├── pdf_report.py
├── pdf_utils.py
├── recruiter_service.py
├── schemas.py
├── semantic_service.py
├── storage.py
├── stripe_billing.py
└── usage_service.py

frontend/
├── .streamlit/
├── pages/
│   ├── admin_analytics.py
│   ├── ats_checker.py
│   ├── cv_rewrite.py
│   ├── history.py
│   ├── landing.py
│   ├── login.py
│   ├── pricing.py
│   ├── recruiter_mode.py
│   ├── register.py
│   └── semantic_match.py
├── app.py
└── auth_utils.py
```

---

## ⚙ Environment Variables

Backend:

```env
OPENAI_API_KEY=

FIREBASE_PROJECT_ID=
FIREBASE_STORAGE_BUCKET=

STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

DATABASE_URL=
```

Frontend:

```toml
BACKEND_URL=""
```

---

## 🚀 Run Locally

Backend

```bash
cd backend

pip install -r requirements.txt

uvicorn main:app --reload
```

Frontend

```bash
cd frontend

pip install -r requirements.txt

streamlit run app.py
```

---

## 🐳 Docker

```bash
docker compose up --build
```

Frontend:

http://localhost:8501

Backend:

http://localhost:8000

---

## 🔥 Firebase

Storage structure:

```text
users/{user_id}/cvs/{timestamp}_{filename}.pdf
```

---

## 💳 Stripe

Webhook:

```text
POST /webhook
```

Stripe automatically upgrades users to Pro.

---

## 🔒 Security

Never commit:

```text
backend/.env
serviceAccountKey.json
frontend/.streamlit/secrets.toml
.venv/
```

---

## 📈 Roadmap

- Better ATS scoring
- AI CV rewrite improvements
- Recruiter dashboard expansion
- PostgreSQL production migration
- Team recruiter accounts

---

## 👨‍💻 Author

Dejan Jović

GitHub:

https://github.com/dejanjovic1283-ui

---

TalentMatch Pro — AI-powered hiring intelligence.
