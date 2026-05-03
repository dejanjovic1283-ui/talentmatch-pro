import os
from datetime import datetime

from firebase import get_bucket


def upload_pdf_to_firebase(
    file_bytes: bytes,
    user_id: int,
    filename: str,
) -> str:
    """Upload a user PDF to Firebase Storage and return the object path."""
    storage_bucket = os.getenv("FIREBASE_STORAGE_BUCKET", "").strip()
    if not storage_bucket:
        return ""

    bucket = get_bucket()

    safe_filename = filename.replace(" ", "_")
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    storage_path = f"users/{user_id}/cvs/{timestamp}_{safe_filename}"

    blob = bucket.blob(storage_path)
    blob.upload_from_string(file_bytes, content_type="application/pdf")

    return storage_path
