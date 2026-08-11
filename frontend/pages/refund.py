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

Last Updated: August 2026

## 1. Overview

TalentMatch Pro operates as a subscription-based SaaS platform that provides AI-powered CV analysis, ATS optimization, CV rewriting, semantic job matching, recruiter insights, candidate ranking, and report generation.

The TalentMatch Pro plan is currently offered for **$19 per month** as a recurring subscription billed through **PayPal**.

This Refund Policy explains when refunds may be available, how cancellations affect future billing, and how refund requests are reviewed.

## 2. Subscription Refunds

Refund requests are reviewed individually.

A refund is not automatically guaranteed after a subscription purchase, renewal, or recurring billing charge.

Each request is reviewed based on the circumstances, service usage, technical issues, and relevant billing records.

## 3. Eligible Refund Situations

Refunds may be granted when:

- A duplicate payment occurred.
- A billing error was identified.
- A technical issue prevented access to paid features.
- The user was charged incorrectly.
- The user paid for TalentMatch Pro access but did not receive access due to a platform-side issue.

## 4. Non-Refundable Situations

Refunds are generally not provided for:

- Change of mind after purchase.
- Partial subscription periods.
- Failure to cancel before a recurring renewal.
- Lack of usage after successful access was provided.
- Dissatisfaction caused by hiring outcomes, employment outcomes, or recruiter decisions.
- Misuse of the platform or violation of the Terms of Service.

## 5. Cancellation

Users may cancel an active TalentMatch Pro subscription through the available **PayPal subscription management** process.

Cancellation prevents future recurring billing in accordance with the subscription status processed by PayPal, but it does not automatically generate a refund for the current or any previous billing period.

After cancellation, access to paid features may remain active until the end of the already paid billing period, depending on the subscription status.

## 6. Processing Time

Approved refunds are processed through **PayPal** and may require several business days to appear on the original payment method.

Actual processing time may depend on PayPal, the user's bank, card issuer, or other financial institution involved in the transaction.

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
- PayPal transaction or subscription details, when available
- Reason for the refund request
- Any relevant screenshots or billing details

Refund requests are reviewed under this Refund Policy and the subscription status associated with the relevant PayPal payment.

## 10. Business Information

TalentMatch Pro  
Owner: Dejan Jovic  
Country: Serbia  
Business Email: [support@talentmatchcv.com](mailto:support@talentmatchcv.com)

## 11. Contact

For billing questions, cancellation questions, or refund requests:

Email: [support@talentmatchcv.com](mailto:support@talentmatchcv.com)
"""
)

render_footer()
