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
# TalentMatch Pro – Privacy Policy

Last Updated: June 2026

## 1. Introduction

TalentMatch Pro respects your privacy and is committed to protecting your personal data.

This Privacy Policy explains what information we collect, how we use it, how we store it, and what rights you have when using TalentMatch Pro.

TalentMatch Pro is an AI-powered SaaS platform for CV analysis, ATS optimization, CV rewriting, semantic job matching, recruiter insights, and candidate ranking.

## 2. Information We Collect

We may collect the following information when you use TalentMatch Pro:

- Name
- Email address
- Account information
- Uploaded CV, resume, or job description files
- Usage information related to analyses, reports, and platform activity
- Technical information such as browser, device, and session data
- Payment and subscription-related information processed securely by our payment provider

We do not intentionally collect sensitive personal data unless it is included by the user inside uploaded CVs, resumes, or job descriptions.

## 3. How We Use Your Information

We use collected information to:

- Create and manage user accounts
- Provide AI-powered CV analysis and job matching
- Generate ATS, semantic match, recruiter, and report outputs
- Improve platform performance and reliability
- Monitor usage limits and plan access
- Provide customer support
- Process subscription and billing requests
- Maintain security and prevent misuse

## 4. CV, Resume, and Document Processing

Users may upload CVs, resumes, and job descriptions for analysis.

Uploaded documents may be processed by AI systems to generate analysis results, recommendations, reports, and matching insights.

Users are responsible for ensuring that uploaded documents are lawful and that they have the right to upload and process them.

## 5. Data Storage

Uploaded documents and generated analysis results may be stored securely for account history, report access, service improvement, and user convenience.

We take reasonable steps to protect stored data against unauthorized access, loss, misuse, or disclosure.

## 6. Third-Party Services

TalentMatch Pro may use trusted third-party services, including:

- Render for hosting and deployment
- OpenAI APIs for AI-powered analysis
- Firebase for authentication and/or storage
- Database and infrastructure providers
- Payment provider for billing and subscription processing
- Analytics and monitoring services

These providers may process data according to their own privacy policies and security practices.

## 7. Payment Information

TalentMatch Pro does not directly store full payment card details.

Payment information is handled securely by our payment provider.

Billing-related data may be used to manage subscriptions, refunds, cancellations, invoices, and access to paid features.

## 8. Security

We implement reasonable technical and organizational measures to protect user data, including:

- Access controls
- Secure authentication
- Environment-based configuration
- Limited access to sensitive systems
- Secure storage practices
- Monitoring and error handling

However, no online service can guarantee absolute security.

## 9. User Rights

Depending on applicable laws, users may request:

- Access to their personal data
- Correction of inaccurate data
- Deletion of their data
- Restriction of processing
- Information about how their data is used

To make a request, contact us using the email address below.

## 10. Data Retention

We retain user information only as long as necessary to provide the service, comply with legal obligations, resolve disputes, prevent abuse, and maintain business records.

Users may request deletion of their data by contacting support.

## 11. Children’s Privacy

TalentMatch Pro is not intended for children under the age of 16.

We do not knowingly collect personal data from children.

## 12. Changes to This Privacy Policy

We may update this Privacy Policy from time to time.

Continued use of TalentMatch Pro after updates means you accept the revised policy.

## 13. Business Information

TalentMatch Pro  
Owner: Dejan Jovic  
Country: Serbia  
Business Email: dejan.jovic1283@gmail.com

## 14. Contact

For privacy questions, data requests, or support:

Email: dejan.jovic1283@gmail.com
"""
)

render_footer()