# TalentMatch Pro — Documentation Index

This directory contains the public documentation and portfolio assets for TalentMatch Pro. Every link must point to a file that exists in the repository and must not expose local paths, secrets, or private user data.

## Structure

```text
docs/
├── README.md
├── architecture/
│   └── architecture.md
├── README-assets/
│   └── banner.png
├── reports/
│   ├── README.md
│   ├── pdf/
│   └── txt/
└── screenshots/
    ├── 01_dashboard.png
    ├── 02_cv_analysis.png
    └── 03_ats_checker.png
```

## Current public screenshots

The root `README.md` uses screenshots captured from the current production UI:

- [Dashboard](screenshots/01_dashboard.png)
- [CV Analysis](screenshots/02_cv_analysis.png)
- [ATS Checker](screenshots/03_ats_checker.png)

Older screenshots may remain in an internal archive, but they must not be presented as the current production interface.

## Documentation

- [System architecture](architecture/architecture.md)
- [Reports index](reports/README.md)
- [Root README](../README.md)

## Banner

The root README uses `docs/README-assets/banner.png`. The file at that path must represent the current production UI, final pricing, active product capabilities, and current product name. Older banners with outdated screens or pricing do not belong in the public showcase.

## Public asset rules

- Never add `.env` values, API keys, passwords, Firebase private JSON files, or tokens.
- Never add private CV documents or personal user data.
- Do not use legacy screenshots as evidence of the current production state.
- Before Git staging, verify that every link and referenced path exists.
- Canonical SEO files belong to the frontend layer: `frontend/static/robots.txt` and `frontend/static/sitemap.xml`.
