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
**Last Updated: September 2026**

## 1. Overview

TalentMatch Pro is a subscription-based SaaS platform that provides AI-powered CV analysis, ATS optimization, CV rewriting, semantic job matching, recruiter insights, candidate ranking, Candidate Database workflows, and report generation.

The Pro plan is currently offered for **$19 USD per month** as a recurring subscription billed through **PayPal**.

This Refund Policy explains when refunds may be available, how cancellations affect future billing, and how refund requests are reviewed.

## 2. Subscription Refunds

Refund requests are reviewed individually.

A refund is not automatically guaranteed after a subscription purchase, renewal, or recurring billing charge.

Each request is reviewed based on the circumstances, service usage, technical issues, relevant billing records, and applicable legal requirements.

## 3. Situations That May Qualify for a Refund

Refunds may be considered when:

- A duplicate payment occurred.
- A billing error was identified.
- A technical issue prevented access to paid features.
- The user was charged incorrectly.
- The user paid for TalentMatch Pro access but did not receive access because of a platform-side issue.

## 4. Situations That Generally Do Not Qualify

Refunds are generally not provided for:

- Change of mind after purchase.
- Unused or partially used subscription time.
- Failure to cancel before a recurring renewal.
- Lack of usage after successful access was provided.
- Dissatisfaction caused by hiring outcomes, employment outcomes, or recruiter decisions.
- Misuse of the platform or violation of the Terms of Service.

This section does not limit any rights that cannot lawfully be excluded under applicable law.

## 5. Cancellation

Users may cancel an active TalentMatch Pro subscription through the available **PayPal subscription management** process.

Cancellation prevents future recurring billing in accordance with the subscription status processed by PayPal. Cancellation does not automatically generate a refund for the current or any previous billing period.

After cancellation, access to paid features may remain active until the end of the already paid billing period, depending on the subscription status and the platform account state.

## 6. Processing Time

Approved refunds are processed through **PayPal** and may require several business days to appear on the original payment method.

Actual processing time may depend on PayPal, the user’s bank, card issuer, or another financial institution involved in the transaction.

## 7. Failed or Interrupted Service

If TalentMatch Pro experiences a temporary outage or technical issue, we will try to restore service as soon as reasonably possible.

Temporary service interruption does not automatically qualify for a refund unless paid access was significantly affected and the issue was caused by TalentMatch Pro. Each request is reviewed individually.

## 8. AI Output Disclaimer

TalentMatch Pro provides AI-generated analysis, suggestions, scores, and recommendations.

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

Do not include passwords or full payment card details in an email.

Refund requests are reviewed under this Refund Policy and the subscription status associated with the relevant PayPal payment.

## 10. Business Information

TalentMatch Pro<br>
Owner: Dejan Jović<br>
Country: Serbia<br>
Business Email: [support@talentmatchcv.com](mailto:support@talentmatchcv.com)

## 11. Contact

For billing questions, cancellation questions, or refund requests:

Email: [support@talentmatchcv.com](mailto:support@talentmatchcv.com)
"""
)

render_footer()
