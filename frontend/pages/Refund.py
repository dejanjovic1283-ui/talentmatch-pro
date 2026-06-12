import streamlit as st

from components.footer import render_footer
from components.sidebar import render_sidebar

st.set_page_config(
    page_title="Refund Policy | TalentMatch Pro",
    page_icon="💸",
    layout="wide",
)

render_sidebar()

st.title("💸 Refund Policy")

st.markdown(
    """
# TalentMatch Pro – Refund Policy

Last Updated: June 2026

## 1. Overview

TalentMatch Pro operates as a subscription-based SaaS platform that provides AI-powered CV analysis, ATS optimization, CV rewriting, semantic job matching, recruiter insights, candidate ranking, and report generation.

This Refund Policy explains when refunds may be available and how refund requests are reviewed.

## 2. Subscription Refunds

Refund requests are reviewed individually.

A refund is not automatically guaranteed after a subscription purchase, renewal, or upgrade.

Each request is reviewed based on the circumstances, service usage, technical issues, and billing records.

## 3. Eligible Refund Situations

Refunds may be granted when:

- A duplicate payment occurred.
- A billing error was identified.
- A technical issue prevented access to paid features.
- The user was charged incorrectly.
- The user paid for Pro access but did not receive access due to a platform-side issue.

## 4. Non-Refundable Situations

Refunds are generally not provided for:

- Change of mind after purchase.
- Partial subscription periods.
- Failure to cancel before renewal.
- Lack of usage after successful access was provided.
- Dissatisfaction caused by hiring outcomes, employment outcomes, or recruiter decisions.
- Misuse of the platform or violation of the Terms of Service.

## 5. Cancellation

Users may cancel subscriptions at any time.

Cancellation prevents future billing but does not automatically generate a refund for the current billing period.

After cancellation, access to paid features may remain active until the end of the paid billing period, depending on the subscription status.

## 6. Processing Time

Approved refunds are processed through our payment provider and may require several business days to appear on the original payment method.

Actual processing time may depend on the payment provider, bank, card issuer, or financial institution.

## 7. Failed or Interrupted Service

If TalentMatch Pro experiences a temporary outage or technical issue, we will try to restore service as soon as possible.

Temporary service interruption does not automatically qualify for a refund unless paid access was significantly affected and the issue was caused by TalentMatch Pro.

## 8. AI Output Disclaimer

TalentMatch Pro provides AI-generated analysis, suggestions, and recommendations.

We do not guarantee:

- Job interviews
- Job offers
- Hiring decisions
- ATS acceptance
- Recruiter approval
- Specific career outcomes

Refunds are not granted solely because a user disagrees with AI-generated results or recommendations.

## 9. How to Request a Refund

To request a refund, contact us by email and include:

- Your full name
- Your account email
- Payment date
- Reason for the refund request
- Any relevant screenshots or billing details

## 10. Business Information

TalentMatch Pro  
Owner: Dejan Jovic  
Country: Serbia  
Business Email: dejan.jovic1283@gmail.com

## 11. Contact

For billing questions, cancellation questions, or refund requests:

Email: dejan.jovic1283@gmail.com
"""
)

render_footer()