# TalentMatch Pro — Architecture Diagrams

## System Architecture

```mermaid
flowchart TD
    U["User"] --> FE["Streamlit frontend"]
    FE --> API["FastAPI backend"]
    API --> AUTH["Firebase Auth and Storage"]
    API --> DB[("PostgreSQL")]
    API --> AI["OpenAI API"]
    API --> PAY["PayPal billing"]
    API --> REP["ReportLab PDF and TXT/CSV exports"]
```

## Production Deployment

```mermaid
flowchart TD
    GH["GitHub main"] --> RF["Render frontend"]
    GH --> RB["Render backend"]
    DOMAIN["talentmatchcv.com"] --> RF
    API_DOMAIN["api.talentmatchcv.com"] --> RB
    RF --> RB
    RB --> PG[("PostgreSQL")]
    RB --> FIREBASE["Firebase"]
    RB --> OPENAI["OpenAI"]
    RB --> PAYPAL["PayPal"]
```

## PayPal Billing Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as Backend
    participant P as PayPal
    participant D as Database

    U->>F: Upgrade to Pro
    F->>B: Subscription request
    B->>P: Create PayPal subscription
    P-->>B: Checkout URL
    B-->>F: Redirect to checkout
    P->>B: Webhook event
    B->>D: Update subscription status
```

## SEO and Static Layer

| Layer | Purpose |
|---|---|
| `frontend/static/robots.txt` | Canonical robots file on the public frontend domain. |
| `frontend/static/sitemap.xml` | Canonical sitemap containing the public product routes. |
| `backend/static/` | Compatibility static files for API routes; not the primary SEO source. |

## Production Rules

- PayPal is the only active billing provider.
- Secrets are supplied through controlled configuration and never committed to Git history.
- Firebase provides authentication and storage, while PostgreSQL stores application data.
- Render hosts separate frontend and backend services.
- Changes pass local validation, Docker smoke testing, Git approval gates, and production verification.
