import streamlit as st

from components.footer import render_footer
from components.sidebar import render_sidebar


st.set_page_config(
    page_title="Terms of Service | TalentMatch Pro",
    page_icon="📃",
    layout="wide",
)

render_sidebar()

st.title("📃 Terms of Service")

st.markdown(
    """
**Last Updated: September 2026**

## 1. Acceptance of Terms

By accessing or using TalentMatch Pro, you agree to be bound by these Terms of Service.

If you do not agree with these Terms, you should not use the platform.

## 2. Description of Service

TalentMatch Pro is an AI-powered SaaS platform that provides tools for job seekers, professionals, recruiters, and small teams.

The platform may include:

- CV analysis
- ATS compatibility checking
- CV rewriting assistance
- Semantic job matching
- Recruiter Mode
- Candidate Database workflows
- Candidate comparison and ranking
- PDF, TXT, and CSV reports
- Saved history
- AI-generated recommendations and insights

## 3. User Accounts

Users may need to create an account to access certain features.

You agree to provide accurate account information and keep your login credentials secure.

You are responsible for activity that occurs under your account and should notify us if you believe that your account has been accessed without authorization.

## 4. User Responsibilities

You agree:

- To provide accurate and lawful information.
- Not to misuse the platform.
- Not to upload illegal, harmful, offensive, or unauthorized content.
- Not to upload documents that you do not have the right to use.
- Not to attempt unauthorized access to the platform, database, API, or infrastructure.
- Not to interfere with the security or performance of the service.
- Not to reverse engineer, scrape, abuse, or overload the platform.

## 5. Uploaded Content

Users may upload CVs, resumes, job descriptions, and related candidate documents.

You remain responsible for the content you upload and for ensuring that you have the right to use it.

By uploading content, you grant TalentMatch Pro permission to process that content for the purpose of providing analysis, reports, recommendations, matching, ranking, and related platform features.

## 6. AI-Generated Results

TalentMatch Pro uses AI systems to generate analysis, summaries, scores, recommendations, and insights.

AI-generated results may contain errors, omissions, or subjective interpretations. Users should review all outputs carefully before relying on them.

TalentMatch Pro does not guarantee that any analysis result will be accepted by employers, recruiters, ATS systems, or hiring platforms.

## 7. Subscriptions and Paid Features

TalentMatch Pro offers a Free workspace and a Pro plan.

The Pro plan is currently offered for **$19 USD per month** as a recurring subscription. Unless expressly stated on the Pricing page, the plan does not include a free trial or setup fee.

Paid subscription billing, recurring payment processing, and subscription management are handled through **PayPal**. The subscription renews automatically until canceled through the available PayPal subscription management process.

Paid features may include unlimited analyses, PDF reports, CV Rewrite AI, Semantic Match, Recruiter Mode, Candidate Database access, candidate ranking, saved history, and recruiter-ready reports.

Subscription access depends on the active subscription status associated with the user account.

TalentMatch Pro may change plan features or pricing in the future. Any updated pricing applies prospectively and will be reflected on the Pricing page before a new subscription or applicable future billing cycle.

## 8. Refunds and Cancellations

Refunds and cancellations are governed by the Refund Policy.

Users may cancel an active TalentMatch Pro subscription through the available PayPal subscription management process.

Cancellation prevents future recurring billing in accordance with the subscription status processed by PayPal. Cancellation does not automatically guarantee a refund for the current or any previous billing period.

Any refund request is evaluated under the Refund Policy applicable at the time of the request and subject to applicable law.

## 9. Intellectual Property

All software, branding, design, text, features, workflows, and content related to TalentMatch Pro remain the property of TalentMatch Pro unless otherwise stated.

Users may not copy, resell, redistribute, clone, or commercially exploit the platform without permission.

## 10. Service Availability

We strive to maintain reliable and uninterrupted service.

However, TalentMatch Pro may be temporarily unavailable due to maintenance, updates, hosting issues, third-party outages, technical errors, or circumstances outside our control.

We do not guarantee continuous availability.

## 11. Third-Party Services

TalentMatch Pro may rely on third-party services for hosting, AI processing, authentication, storage, payments, and infrastructure, including Render, OpenAI, Firebase, PostgreSQL-related infrastructure, and PayPal.

We are not responsible for third-party service interruptions, policy changes, failures, delays, or data processing practices.

## 12. Limitation of Liability

TalentMatch Pro is provided "as is" and "as available" without warranties of any kind.

To the maximum extent permitted by law, TalentMatch Pro is not responsible for:

- Employment outcomes
- Hiring decisions
- Job application results
- ATS rejection or acceptance
- Recruiter decisions
- User misuse of AI-generated content
- Loss of data caused by third-party services
- Temporary service interruptions
- Indirect, incidental, or consequential damages

Nothing in these Terms excludes or limits liability that cannot lawfully be excluded or limited.

## 13. No Employment Guarantee

TalentMatch Pro helps users improve CVs, analyze job descriptions, and understand skill gaps.

The platform does not guarantee job offers, interviews, employment, recruiter responses, or career success.

## 14. Account Suspension or Termination

We may suspend or terminate access if a user violates these Terms, misuses the platform, attempts unauthorized access, uploads harmful content, or abuses free or paid features.

Where appropriate, we may take reasonable steps to protect users, the platform, and third-party services.

## 15. Changes to Terms

We may update these Terms of Service from time to time.

The updated version will be published on this page with a revised update date. Continued use of TalentMatch Pro after an update means that you acknowledge the revised Terms, to the extent permitted by applicable law.

## 16. Business Information

TalentMatch Pro<br>
Owner: Dejan Jović<br>
Country: Serbia<br>
Business Email: [support@talentmatchcv.com](mailto:support@talentmatchcv.com)

## 17. Contact

For questions regarding these Terms:

Email: [support@talentmatchcv.com](mailto:support@talentmatchcv.com)
"""
)

render_footer()
