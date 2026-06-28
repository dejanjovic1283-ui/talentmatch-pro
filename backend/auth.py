from __future__ import annotations

import os
from typing import Any

import requests
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from db import get_db
from models import User

bearer_scheme = HTTPBearer(auto_error=False)


def _clean_text(value: Any) -> str:
    """Return a safe, stripped string value."""
    if value is None:
        return ""
    return str(value).strip()


def _clean_display_name(value: Any) -> str:
    """Normalize Firebase/profile names for consistent UI display."""
    raw = _clean_text(value)
    if not raw:
        return ""

    if "@" in raw:
        raw = raw.split("@", 1)[0]

    raw = raw.replace(".", " ").replace("_", " ").replace("-", " ")
    raw = __import__("re").sub(r"[0-9]+", "", raw)
    raw = __import__("re").sub(r"(?<=[a-z])(?=[A-Z])", " ", raw)
    raw = __import__("re").sub(r"\s+", " ", raw).strip()

    if not raw:
        return ""

    parts = [part for part in raw.split() if part]
    display_name = " ".join(part[:1].upper() + part[1:].lower() for part in parts[:3])
    compact = __import__("re").sub(r"[^a-zA-Z]", "", display_name).lower()
    if "dejan" in compact and "jovic" in compact:
        return "Dejan Jovic"
    return display_name


def _name_from_email(email: str) -> str:
    """Create a friendly fallback name from an email address."""
    return _clean_display_name(email) or "TalentMatch User"


def _firebase_display_name(firebase_user: dict[str, Any], email: str) -> str:
    """Read the best available display name from Firebase lookup data."""
    direct_name = _clean_display_name(firebase_user.get("displayName"))
    if direct_name:
        return direct_name

    providers = firebase_user.get("providerUserInfo") or []
    if isinstance(providers, list):
        for provider in providers:
            if not isinstance(provider, dict):
                continue
            provider_name = _clean_display_name(provider.get("displayName"))
            if provider_name:
                return provider_name

    return _name_from_email(email)


def verify_firebase_token_with_rest(token: str) -> dict[str, Any]:
    """Verify a Firebase ID token through the Firebase Identity Toolkit REST API."""
    api_key = os.getenv("FIREBASE_API_KEY", "")

    if not api_key:
        raise HTTPException(status_code=401, detail="FIREBASE_API_KEY missing on backend.")

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={api_key}"

    try:
        response = requests.post(url, json={"idToken": token}, timeout=30)
    except requests.RequestException as exc:
        raise HTTPException(status_code=401, detail=f"Firebase verification failed: {exc}") from exc

    if response.status_code != 200:
        print("FIREBASE REST VERIFY ERROR:", response.text)
        raise HTTPException(status_code=401, detail="Invalid Firebase token.")

    try:
        data = response.json()
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Firebase returned invalid verification response.") from exc

    users = data.get("users", [])

    if not users:
        raise HTTPException(status_code=401, detail="Firebase user not found.")

    first_user = users[0]
    if not isinstance(first_user, dict):
        raise HTTPException(status_code=401, detail="Invalid Firebase user payload.")

    return first_user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Return the authenticated app user and keep profile fields synced."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing Authorization Bearer token.")

    token = credentials.credentials.strip()

    if not token:
        raise HTTPException(status_code=401, detail="Empty Firebase token.")

    firebase_user = verify_firebase_token_with_rest(token)

    firebase_uid = _clean_text(firebase_user.get("localId"))
    email = _clean_text(firebase_user.get("email")).lower()
    full_name = _firebase_display_name(firebase_user, email)

    if not firebase_uid:
        raise HTTPException(status_code=401, detail="Firebase UID missing.")

    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()

    if not user:
        user = User(
            firebase_uid=firebase_uid,
            email=email,
            full_name=full_name,
            plan="free",
            is_pro=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    changed = False

    if email and getattr(user, "email", None) != email:
        user.email = email
        changed = True

    current_name = _clean_text(getattr(user, "full_name", ""))
    normalized_current_name = _clean_display_name(current_name)
    if full_name and current_name != full_name:
        user.full_name = full_name
        changed = True
    elif normalized_current_name and current_name != normalized_current_name:
        user.full_name = normalized_current_name
        changed = True

    if changed:
        db.add(user)
        db.commit()
        db.refresh(user)

    return user


def get_test_user(db: Session = Depends(get_db)) -> User:
    """Return a local development user for test-only endpoints."""
    user = db.query(User).filter(User.email == "local-test@talentmatch.dev").first()

    if user:
        return user

    user = User(
        firebase_uid="local-test-user",
        email="local-test@talentmatch.dev",
        full_name="Local Test User",
        plan="free",
        is_pro=False,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user
