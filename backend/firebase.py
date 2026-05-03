import json
import os
import ssl
import tempfile
from pathlib import Path

import certifi
import firebase_admin
from firebase_admin import credentials, storage

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
ssl._create_default_https_context = ssl.create_default_context(
    cafile=certifi.where()
)


def init_firebase() -> None:
    """Initialize Firebase Admin SDK once for local and production environments."""
    if firebase_admin._apps:
        return

    storage_bucket = os.getenv("FIREBASE_STORAGE_BUCKET", "").strip()
    project_id = os.getenv("FIREBASE_PROJECT_ID", "").strip()
    firebase_credentials_json = os.getenv("FIREBASE_CREDENTIALS", "").strip()
    service_account_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()

    if firebase_credentials_json:
        service_account_data = json.loads(firebase_credentials_json)

        temp_file = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            encoding="utf-8",
        )
        json.dump(service_account_data, temp_file)
        temp_file.close()

        cred = credentials.Certificate(temp_file.name)

    else:
        if not service_account_path:
            service_account_path = "./serviceAccountKey.json"

        service_account_file = Path(service_account_path)

        if not service_account_file.exists():
            raise RuntimeError(
                f"Firebase service account file not found: {service_account_file}"
            )

        cred = credentials.Certificate(str(service_account_file))

    if not storage_bucket:
        raise RuntimeError("FIREBASE_STORAGE_BUCKET is missing.")

    options = {
        "storageBucket": storage_bucket,
    }

    if project_id:
        options["projectId"] = project_id

    firebase_admin.initialize_app(cred, options)


def get_bucket():
    """Return the configured Firebase Storage bucket."""
    init_firebase()
    return storage.bucket()