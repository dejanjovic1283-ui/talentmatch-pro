import os
import ssl
from pathlib import Path

import certifi
import firebase_admin
from firebase_admin import credentials, storage

# Make SSL trust stores explicit to reduce local certificate issues.
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
ssl._create_default_https_context = ssl.create_default_context(cafile=certifi.where())


def init_firebase() -> None:
    """Initialize Firebase Admin only once per process."""
    if firebase_admin._apps:
        return

    service_account_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()

    # Local development fallback.
    if not service_account_path:
        service_account_path = "./serviceAccountKey.json"

    service_account_file = Path(service_account_path)

    if not service_account_file.exists():
        raise RuntimeError(f"Firebase service account file not found: {service_account_file}")

    storage_bucket = os.getenv("FIREBASE_STORAGE_BUCKET", "").strip()
    project_id = os.getenv("FIREBASE_PROJECT_ID", "").strip()

    if not storage_bucket:
        raise RuntimeError("FIREBASE_STORAGE_BUCKET is missing.")

    options = {
        "storageBucket": storage_bucket,
    }

    if project_id:
        options["projectId"] = project_id

    cred = credentials.Certificate(str(service_account_file))
    firebase_admin.initialize_app(cred, options)


def get_bucket():
    """Return the configured Firebase Storage bucket."""
    init_firebase()
    return storage.bucket()