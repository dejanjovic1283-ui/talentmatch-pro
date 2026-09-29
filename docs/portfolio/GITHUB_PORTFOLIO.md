# TalentMatch Pro™ — GitHub Portfolio Presentation

![TalentMatch Pro production banner](assets/talentmatch-pro-banner.png)

> Production AI SaaS for resume intelligence, ATS optimisation, semantic candidate matching, recruiter workflows, and professional reporting.

[Open the live application](https://talentmatchcv.com) · [Production API](https://api.talentmatchcv.com) · [API documentation](https://api.talentmatchcv.com/docs) · [Source repository](https://github.com/dejanjovic1283-ui/talentmatch-pro)

## Project snapshot

TalentMatch Pro is a production-oriented platform for job seekers, recruiters, and hiring workflows. It combines resume analysis, ATS-oriented feedback, AI-assisted rewriting, semantic matching, candidate ranking, persistent history, and exportable reports in one web workspace.

The application is designed as a real SaaS product rather than a standalone model demo. The public deployment includes authentication, persistent sessions, subscription entitlements, PayPal billing, PostgreSQL-backed data, secure API boundaries, operational health checks, and production reporting.

## Product surface

| Area | What it provides |
| --- | --- |
| CV Analysis | Structured resume intelligence, scoring, findings, and recommendations against a target role. |
| ATS Checker | ATS-oriented score, matched and missing keywords, coverage guidance, and export-ready results. |
| CV Rewrite | Role-aligned rewriting with positioning improvements, ATS context, and report output. |
| Semantic Match | Contextual similarity across skills, keywords, themes, and role relevance. |
| Recruiter Mode | Candidate review, ranking, strengths, gaps, recruiter recommendations, and exports. |
| Candidate Database | Persistent recruiter workspace for saving, reviewing, organizing, and revisiting candidates. |
| History | Saved analysis records, filters, report detail, retention controls, and PDF/TXT exports. |
| Account and Pricing | Secure account workspace, Pro entitlement visibility, usage information, and PayPal subscription controls. |

## Architecture at a glance

```mermaid
flowchart TD
    U[Users] --> F[Streamlit frontend]
    F --> B[FastAPI backend]
    B --> AI[OpenAI analysis and semantic services]
    B --> DB[(PostgreSQL persistence)]
    B --> AUTH[Firebase authentication and storage]
    B --> PAY[PayPal Live billing]
    B --> RPT[ReportLab PDF, TXT, and CSV exports]
```

## Technology stack

| Layer | Production technology |
| --- | --- |
| Frontend | Streamlit, responsive workspace UI, 12 locales, dark/light/system themes |
| Backend | FastAPI, Python, protected API routes, structured error responses |
| AI | OpenAI-powered analysis, rewriting, scoring, and semantic matching |
| Data | PostgreSQL for persistent application state and workflow records |
| Identity and files | Firebase Authentication and Firebase Storage |
| Billing | PayPal Live subscriptions, Pro plan at `$19/month` |
| Reporting | ReportLab with Unicode and multilingual PDF support, plus TXT/CSV exports |
| Runtime and delivery | Docker, Render, Cloudflare, custom production domains |

## Engineering evidence

The project demonstrates the following production concerns in the deployed system:

- authenticated frontend-to-backend access with server-side authorization;
- PostgreSQL-backed history, candidate data, usage, and session persistence;
- durable browser sessions with explicit sign-in and sign-out behavior;
- Pro entitlement persistence and unlimited Pro CV analysis;
- PayPal-only subscription flow and subscription-settings handoff;
- request IDs, structured logs, health/readiness endpoints, and standardized JSON errors;
- rate limiting, timeout protection, retry policies, circuit breakers, and graceful degradation;
- HTTPS redirect, HSTS, trusted-host checks, security headers, CORS controls, and no secret logging;
- ETag and conditional GET support, cache-control policies, and GZip compression;
- Unicode PDF generation for English, Serbian Latin, Cyrillic, Arabic, and other supported locales;
- production SEO routes for canonical pages, `robots.txt`, and `sitemap.xml`.

## Production endpoints

| Endpoint | Purpose |
| --- | --- |
| [`talentmatchcv.com`](https://talentmatchcv.com) | Public application |
| [`api.talentmatchcv.com/healthz`](https://api.talentmatchcv.com/healthz) | Backend health check |
| [`api.talentmatchcv.com/readyz`](https://api.talentmatchcv.com/readyz) | Dependency and configuration readiness |
| [`api.talentmatchcv.com/docs`](https://api.talentmatchcv.com/docs) | API documentation |
| [`talentmatchcv.com/robots.txt`](https://talentmatchcv.com/robots.txt) | Crawler policy |
| [`talentmatchcv.com/sitemap.xml`](https://talentmatchcv.com/sitemap.xml) | Public route index |

## Selected product evidence

The public gallery focuses on the actual product surface. The full README and technical evidence remain available in the repository documentation.

### Dashboard

![TalentMatch Pro dashboard](assets/01-dashboard.png)

Production workspace overview with user context, feature access, and navigation.

### CV Analysis

![TalentMatch Pro CV Analysis](assets/02-cv-analysis.png)

Resume analysis workflow with score, findings, and export-ready results.

### ATS Checker

![TalentMatch Pro ATS Checker](assets/03-ats-checker.png)

ATS-oriented score, matched keywords, missing keywords, and recommendations.

### CV Rewrite

![TalentMatch Pro CV Rewrite](assets/04-cv-rewrite.png)

Role-aligned rewriting workflow with ATS enrichment and report output.

### Semantic Match

![TalentMatch Pro Semantic Match](assets/05-semantic-match.png)

Semantic, keyword, and overall-match intelligence for role and candidate relevance.

### Recruiter Mode

![TalentMatch Pro Recruiter Mode](assets/06-recruiter-mode.png)

Candidate ranking, strengths, gaps, leaderboard, and recruiter report exports.

### Candidate Database

![TalentMatch Pro Candidate Database](assets/07-candidate-database.png)

Persistent recruiter candidate pipeline, evidence, notes, and controls.

### History

![TalentMatch Pro History](assets/08-history.png)

Saved report history with filtering, exports, report detail, and retention controls.

### Pricing

![TalentMatch Pro pricing](assets/09-pricing.png)

Free and Pro plan comparison, including the `$19/month` PayPal subscription.

### Account

![TalentMatch Pro account](assets/10-account.png)

Account workspace with Pro membership, usage, system health, security, and session controls.

### Secure login session

![TalentMatch Pro secure login session](assets/11-secure-login-session.png)

Login, active secure session, dashboard access, and verified account state.

### SEO and indexing

![TalentMatch Pro SEO indexing](assets/12-seo-indexing.png)

Production `robots.txt` and `sitemap.xml` routes used for crawl and indexing readiness.

## Founder

![Dejan Jović — Founder and developer](assets/dejan-jovic-portfolio.jpg)

**Dejan Jović** is the founder and developer of TalentMatch Pro, responsible for the product direction, application architecture, production implementation, deployment, reporting system, and end-to-end delivery.

[Personal GitHub portfolio](https://github.com/dejanjovic1283-ui) · [LinkedIn](https://www.linkedin.com/in/dejan-jović-5babb538a)

## Education and certifications

The following qualifications support the technical focus of the product. Examination percentages and ranking positions are intentionally omitted from this public portfolio presentation.

### EITCA Artificial Intelligence

- EITCA/AI Artificial Intelligence Programme
- EITC/AI/ADL — Advanced Deep Learning
- EITC/AI/ARL — Advanced Reinforcement Learning
- EITC/AI/DLPP — Deep Learning with Python and PyTorch
- EITC/AI/DLPTFK — Deep Learning with Python, TensorFlow and Keras
- EITC/AI/DLTF — Deep Learning with TensorFlow
- EITC/AI/GCML — Google Cloud Machine Learning
- EITC/AI/GVAPI — Google Vision API
- EITC/AI/MLP — Machine Learning with Python
- EITC/AI/TFF — TensorFlow Fundamentals
- EITC/AI/TFQML — TensorFlow Quantum Machine Learning
- EITC/CL/GCP — Google Cloud Platform
- EITC/CP/PPF — Python Programming Fundamentals

### ITAcademy — AI & Python Development

- Introduction to Python Programming
- Object-Oriented Python and Core Data Structures
- Data Analysis and Processing with Python
- Interactive Data Analysis and Visualization with Python
- Databases and SQL for Data Science with Python
- Introduction to Machine Learning using Python
- R for Data Science and Data Analytics
- Cloud Data Engineering Tools
- Computer Use Basics
- Introduction to Git and GitHub
- Introduction to AI Tools — ChatGPT and Midjourney

## Release context

**TalentMatch Pro v3.0 FINAL** is the completed production baseline. The live application, API, authentication, persistence, AI workflows, billing, reporting, security controls, deployment configuration, and documentation are aligned around the production release.

## Ownership and support

Support: [support@talentmatchcv.com](mailto:support@talentmatchcv.com)

TalentMatch Pro™ © 2026 Dejan Jović. All rights reserved. This repository is public for portfolio and evaluation purposes only. No license is granted to copy, redistribute, modify, commercialise, or reuse the source, design, branding, screenshots, reports, or documentation without written permission.

See the [complete root README](../../README.md) for the full technical reference, local development instructions, repository structure, architecture notes, and production acceptance record.
