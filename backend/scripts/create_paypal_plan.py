import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

# Load backend/.env even when this script is started from backend/scripts
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=ENV_PATH)

PAYPAL_ENV = os.getenv("PAYPAL_ENV", "live").lower()
PAYPAL_CLIENT_ID = os.environ["PAYPAL_CLIENT_ID"]
PAYPAL_CLIENT_SECRET = os.environ["PAYPAL_CLIENT_SECRET"]

BASE_URL = (
    "https://api-m.paypal.com"
    if PAYPAL_ENV == "live"
    else "https://api-m.sandbox.paypal.com"
)


def get_access_token() -> str:
    response = requests.post(
        f"{BASE_URL}/v1/oauth2/token",
        auth=HTTPBasicAuth(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
        data={"grant_type": "client_credentials"},
        headers={
            "Accept": "application/json",
            "Accept-Language": "en_US",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def create_product(access_token: str) -> dict:
    response = requests.post(
        f"{BASE_URL}/v1/catalogs/products",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        json={
            "name": "TalentMatch Pro",
            "description": "AI-powered CV analysis and ATS optimization platform.",
            "type": "SERVICE",
            "category": "SOFTWARE",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def create_plan(access_token: str, product_id: str) -> dict:
    response = requests.post(
        f"{BASE_URL}/v1/billing/plans",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        json={
            "product_id": product_id,
            "name": "TalentMatch Pro Monthly",
            "description": "TalentMatch Pro subscription - $9/month.",
            "status": "ACTIVE",
            "billing_cycles": [
                {
                    "frequency": {
                        "interval_unit": "MONTH",
                        "interval_count": 1,
                    },
                    "tenure_type": "REGULAR",
                    "sequence": 1,
                    "total_cycles": 0,
                    "pricing_scheme": {
                        "fixed_price": {
                            "value": "9.00",
                            "currency_code": "USD",
                        }
                    },
                }
            ],
            "payment_preferences": {
                "auto_bill_outstanding": True,
                "setup_fee_failure_action": "CONTINUE",
                "payment_failure_threshold": 3,
            },
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    print(f"PayPal environment: {PAYPAL_ENV}")
    print(f"PayPal API base URL: {BASE_URL}")
    print()

    access_token = get_access_token()

    product = create_product(access_token)
    product_id = product["id"]

    plan = create_plan(access_token, product_id)
    plan_id = plan["id"]

    print("✅ PayPal Product created:")
    print(product_id)
    print()
    print("✅ PayPal Plan created:")
    print(plan_id)
    print()
    print("Add this to backend/.env and Render Environment:")
    print(f"PAYPAL_PLAN_ID={plan_id}")


if __name__ == "__main__":
    main()
