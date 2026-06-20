import os
from sqlalchemy.orm import sessionmaker

from db import engine
from models import User


TARGET_EMAIL = os.getenv("TARGET_EMAIL", "dejanjovic1283@gmail.com")
TARGET_PLAN = os.getenv("TARGET_PLAN", "pro")
TARGET_STATUS = os.getenv("TARGET_STATUS", "manual_test_pro")


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def main() -> None:
    db = SessionLocal()

    try:
        user = db.query(User).filter(User.email == TARGET_EMAIL).first()

        if user is None:
            raise SystemExit(f"User not found: {TARGET_EMAIL}")

        user.plan = TARGET_PLAN
        user.is_pro = TARGET_PLAN.lower() == "pro"

        if hasattr(user, "paypal_subscription_status"):
            user.paypal_subscription_status = TARGET_STATUS

        db.add(user)
        db.commit()
        db.refresh(user)

        print("User updated successfully.")
        print(f"Email: {user.email}")
        print(f"Plan: {user.plan}")
        print(f"is_pro: {user.is_pro}")
        print(f"PayPal status: {getattr(user, 'paypal_subscription_status', None)}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
