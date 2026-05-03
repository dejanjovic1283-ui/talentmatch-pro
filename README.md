# 🚀 TalentMatch Pro

TalentMatch Pro is an AI-powered SaaS platform that helps users compare their CV against a real job description, receive a match score, identify missing skills, and get actionable improvement recommendations.

## ✨ Features

- Firebase email/password authentication
- PDF CV upload
- AI-powered CV analysis with OpenAI
- Match score from 0 to 100
- Strengths, weaknesses, and recommendations
- Firebase Storage for uploaded CV files
- Analysis history saved in the database
- Free plan analysis limit
- Lemon Squeezy-ready upgrade flow
- FastAPI backend
- Streamlit frontend

## 🧱 Tech Stack

- Backend: FastAPI, SQLAlchemy, Pydantic
- Frontend: Streamlit
- Auth: Firebase Authentication
- Storage: Firebase Storage
- AI: OpenAI API
- Billing: Lemon Squeezy
- Database: SQLite locally, PostgreSQL in production
- Deployment: Render + Streamlit Community Cloud
- Docker: Optional local full-stack setup

## 📁 Project Structure

talentmatch-pro/
├── backend/
│   ├── auth.py
│   ├── billing.py
│   ├── db.py
│   ├── firebase.py
│   ├── main.py
│   ├── models.py
│   ├── openai_service.py
│   ├── pdf_utils.py
│   ├── requirements.txt
│   ├── schemas.py
│   └── storage.py
│
├── frontend/
│   ├── .streamlit/
│   │   └── secrets.toml.example
│   ├── pages/
│   │   └── pricing.py
│   ├── app.py
│   └── requirements.txt
│
├── .gitignore
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
└── README.md

## 🧪 Local Testing Checklist

Before pushing to GitHub or deploying, verify the full local flow:

1. Start the backend:

- cd backend
- .venv\Scripts\activate
- uvicorn main:app --reload

2. Start the frontend:

- cd frontend
- .venv\Scripts\activate
- streamlit run app.py

3. Open the app:
- http://localhost:8501
4. Sign in with Firebase email/password.
5. Upload a PDF CV.
6. Paste a job description.
7. Click "Analyze CV".

**Expected result:**

- The backend validates the Firebase ID token.
- The PDF text is extracted.
- OpenAI returns a score and recommendations.
- The PDF is uploaded to Firebase Storage.
- The analysis is saved in the database.
- The frontend displays the result.

## 📦 Firebase Storage Structure

**Uploaded CV files are stored per user:**

users/{user_id}/cvs/{timestamp}_{filename}.pdf

**Example:**

users/1/cvs/20260503002521_20260501_cv1.pdf

- This structure keeps user files separated and ready for production SaaS usage.

## 🧾 Free Plan Logic

- Free users have a limited number of analyses.

**The limit is controlled by:**
FREE_PLAN_ANALYSIS_LIMIT=3

- When the user reaches the free plan limit, the backend returns an upgrade message.
- Pro users can continue using the analysis flow without the free-plan limit.

## 💳 Lemon Squeezy Upgrade Flow

**The frontend shows an upgrade option using:**
LEMON_SQUEEZY_CHECKOUT_URL = "https://your-store.lemonsqueezy.com/buy/your-checkout-id"

- After payment, Lemon Squeezy sends a webhook request to the backend.

**Webhook endpoint:**
POST /webhook

**Production webhook URL example:**
https://your-render-backend.onrender.com/webhook

- The backend verifies the webhook signature and upgrades the user to Pro.

## 🚀 Production Deployment Order

**Recommended deployment order:**

1. Confirm local backend works.
2. Confirm local frontend works.
3. Confirm Firebase Auth works.
4. Confirm Firebase Storage upload works.
5. Confirm OpenAI analysis works.
6. Push to GitHub.
7. Deploy backend to Render.
8. Deploy frontend to Streamlit Community Cloud.
9. Add production secrets.
10. Test the production flow end-to-end.
11. Configure Lemon Squeezy webhook.
12. Run final production test.

## 🛡️ Security Notes

**Never expose or commit:**

- backend/.env
- backend/serviceAccountKey.json
- backend/talentmatch.db
- frontend/.streamlit/secrets.toml
- get_token.py
- .venv/

**Firebase ID tokens must be sent only through the Authorization header:**
- Authorization: Bearer <firebase_id_token>

- The backend must always verify tokens with Firebase Admin SDK.

## 🐳 Docker Notes

- Docker is optional for local development.
- Use Docker only after the backend and frontend work locally without Docker.

**Run from the project root:**
docker compose up --build

**Expected URLs:**
Backend: http://127.0.0.1:8000
Frontend: http://localhost:8501

## ✅ MVP Completion Criteria

**The MVP is considered working when:**

- Users can sign in.
- Users can upload a PDF CV.
- Users can paste their own job description.
- AI returns a match score.
- Firebase Storage receives the uploaded CV.
- The database stores the analysis record.
- The free-plan limit works.
- The upgrade path is visible.

## 📌 Roadmap

**Planned improvements:**

- Better Firebase login UI
- Analysis history page
- Pro dashboard
- Lemon Squeezy production webhook
- Render backend deployment
- Streamlit Cloud frontend deployment
- PostgreSQL production database
- PDF report export
- Recruiter-facing dashboard
- LinkedIn launch campaign

## 👨‍💻 Author

**Dejan Jović**

**GitHub: dejanjovic1283-ui**
**Email: dejan.jovic1283@gmail.com**