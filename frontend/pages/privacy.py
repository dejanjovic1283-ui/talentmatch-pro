import streamlit as st

from components.footer import render_footer
from components.sidebar import render_sidebar


st.set_page_config(
    page_title="Privacy Policy | TalentMatch Pro",
    page_icon="🔒",
    layout="wide",
)

render_sidebar()

st.title("🔒 Privacy Policy")

st.markdown(
    """
**Last Updated: September 2026**

## 1. Introduction

TalentMatch Pro respects your privacy and is committed to protecting your personal data.

This Privacy Policy explains what information we collect, how we use it, how we store it, and what rights you may have when using TalentMatch Pro.

TalentMatch Pro is an AI-powered SaaS platform for CV analysis, ATS optimization, CV rewriting, semantic job matching, recruiter insights, candidate ranking, Candidate Database workflows, and report generation.

## 2. Information We Collect

We may collect the following information when you use TalentMatch Pro:

- Name and email address
- Account and authentication information
- Uploaded CV, resume, job description, or candidate files
- Usage information related to analyses, reports, history, and platform activity
- Technical information such as browser, device, session, request, and security data
- Payment and subscription-related information processed by PayPal

We do not intentionally request sensitive personal data. However, users may include personal or sensitive information in documents they upload, and users remain responsible for ensuring that they have the right to upload and process those documents.

## 3. How We Use Your Information

We use collected information to:

- Create and manage user accounts
- Provide CV analysis, ATS checking, rewriting, matching, and recruiter workflows
- Generate scores, recommendations, summaries, and reports
- Save and display relevant history and account activity
- Improve platform performance and reliability
- Monitor usage limits and plan access
- Provide customer support
- Process subscription, billing, cancellation, and refund requests
- Maintain security and prevent misuse

## 4. CV, Resume, and Document Processing

Users may upload CVs, resumes, job descriptions, and candidate-related documents for analysis.

Uploaded documents may be processed by AI systems and related platform services to generate analysis results, recommendations, reports, and matching insights.

Users are responsible for ensuring that uploaded documents are lawful and that they have the right to upload and process the information they contain.

## 5. Data Storage and Retention

Uploaded documents, account information, and generated analysis results may be stored securely for account history, report access, service operation, security, and user convenience.

We retain information only as long as reasonably necessary to provide the service, comply with legal obligations, resolve disputes, prevent abuse, and maintain appropriate business records.

Users may request deletion of their data by contacting support. Some information may need to be retained where required by law, for security, or to resolve disputes.

## 6. Third-Party Services

TalentMatch Pro may use trusted third-party services, including:

- Render for hosting and deployment
- OpenAI APIs for AI-powered analysis
- Firebase for authentication and storage
- PostgreSQL and related infrastructure providers for application data
- PayPal for billing and recurring subscription processing
- Security, monitoring, and operational services needed to run the platform

These providers may process data according to their own terms and privacy policies.

## 7. Payment Information

TalentMatch Pro does not directly store full payment card details.

Payment and subscription information is handled by PayPal. Billing-related data may be used to manage subscriptions, cancellations, refunds, invoices, and access to paid features.

The current Pro plan is **$19 USD per month** as a recurring PayPal subscription. The applicable plan information is shown on the Pricing page.

## 8. Security

We implement reasonable technical and organizational measures to protect user data, including:

- Secure authentication and access controls
- Environment-based configuration for sensitive settings
- Limited access to production systems
- Secure storage practices
- Request monitoring, error handling, and operational safeguards

However, no online service can guarantee absolute security.

## 9. User Rights

Depending on applicable law, users may request:

- Access to their personal data
- Correction of inaccurate data
- Deletion of their data
- Restriction of processing
- Information about how their data is used

To make a request, contact us using the email address below.

## 10. Children’s Privacy

TalentMatch Pro is not intended for children under the age of 16.

We do not knowingly collect personal data from children.

## 11. Changes to This Privacy Policy

We may update this Privacy Policy from time to time.

The updated version will be published on this page with a revised update date. Continued use of TalentMatch Pro after an update means that you acknowledge the revised policy, to the extent permitted by applicable law.

## 12. Business Information

TalentMatch Pro<br>
Owner: Dejan Jović<br>
Country: Serbia<br>
Business Email: [support@talentmatchcv.com](mailto:support@talentmatchcv.com)

## 13. Contact

For privacy questions, data requests, or support:

Email: [support@talentmatchcv.com](mailto:support@talentmatchcv.com)
"""
)

render_footer()
