from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth
from sqlalchemy.orm import Session

from db import get_db
from firebase import init_firebase
from models import User

# Use Bearer auth so the Streamlit app can pass the Firebase ID token.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validate the Firebase ID token and upsert the local user record."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing Authorization Bearer token.")

    token = credentials.credentials.strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty Firebase token.")

    try:
        init_firebase()
        decoded = firebase_auth.verify_id_token(token)
    except Exception as exc:
        print("FIREBASE TOKEN VERIFY ERROR:", exc)
        raise HTTPException(status_code=401, detail="Invalid Firebase token.")

    firebase_uid = decoded.get("uid")
    email = decoded.get("email") or ""

    if not firebase_uid:
        raise HTTPException(status_code=401, detail="Firebase UID missing.")

    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()

    if not user:
        user = User(
            firebase_uid=firebase_uid,
            email=email,
            full_name=email or None,
            plan="free",
            is_pro=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return user

def get_test_user(db: Session = Depends(get_db)) -> User:
    """Return a stable local development user without requiring Firebase Auth."""

    user = db.query(User).filter(User.email == "local-test@talentmatch.dev").first()

    if user:
        return user

    user = User(
        firebase_uid="local-test-user",
        email="local-test@talentmatch.dev",
        full_name="Local Test User",
        plan="pro",
        is_pro=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user