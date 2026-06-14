import os
import requests
from requests.auth import HTTPBasicAuth

PAYPAL_ENV = os.getenv("PAYPAL_ENV", "live").lower()
CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")

BASE_URL = "https://api-m.paypal.com" if PAYPAL_ENV == "live" else "https://api-m.sandbox.paypal.com"

if not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError("Missing PAYPAL_CLIENT_ID or PAYPAL_CLIENT_SECRET")


def get_access_token():
    response = requests.post(
        f"{BASE_URL}/v1/oauth2/token",
        auth=HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET),
        data={"grant_type": "client_credentials"},
        headers={"Accept": "application/json", "Accept-Language": "en_US"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def create_product(token):
    response = requests.post(
        f"{BASE_URL}/v1/catalogs/products",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
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


def create_plan(token, product_id):
    response = requests.post(
        f"{BASE_URL}/v1/billing/plans",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        json={
            "product_id": product_id,
            "name": "TalentMatch Pro Monthly",
            "description": "TalentMatch Pro subscription - $9/month.",
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


def main():
    token = get_access_token()

    product = create_product(token)
    product_id = product["id"]

    plan = create_plan(token, product_id)
    plan_id = plan["id"]

    print("✅ PayPal Product created:")
    print(product_id)
    print()
    print("✅ PayPal Plan created:")
    print(plan_id)
    print()
    print("Add this to Render backend Environment:")
    print(f"PAYPAL_PLAN_ID={plan_id}")


if __name__ == "__main__":
    main()