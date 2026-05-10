import os
import requests
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from db import get_db
from models import User

bearer_scheme = HTTPBearer(auto_error=False)


def verify_firebase_token_with_rest(token: str) -> dict:
    api_key = os.getenv("FIREBASE_API_KEY", "")

    if not api_key:
        raise HTTPException(status_code=401, detail="FIREBASE_API_KEY missing on backend.")

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={api_key}"
    response = requests.post(url, json={"idToken": token}, timeout=30)

    if response.status_code != 200:
        print("FIREBASE REST VERIFY ERROR:", response.text)
        raise HTTPException(status_code=401, detail="Invalid Firebase token.")

    data = response.json()
    users = data.get("users", [])

    if not users:
        raise HTTPException(status_code=401, detail="Firebase user not found.")

    return users[0]


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing Authorization Bearer token.")

    token = credentials.credentials.strip()

    if not token:
        raise HTTPException(status_code=401, detail="Empty Firebase token.")

    firebase_user = verify_firebase_token_with_rest(token)

    firebase_uid = firebase_user.get("localId")
    email = firebase_user.get("email", "")

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