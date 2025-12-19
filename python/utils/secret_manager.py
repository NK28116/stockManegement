import os
from typing import Optional

try:
    from google.cloud import secretmanager
    SECRET_MANAGER_AVAILABLE = True
except ImportError:
    SECRET_MANAGER_AVAILABLE = False

def get_secret(secret_id: str, version_id: str = "latest") -> Optional[str]:
    """
    Retrieves a secret from Google Cloud Secret Manager.
    """
    if not SECRET_MANAGER_AVAILABLE:
        print("[WARNING] google-cloud-secret-manager not installed.")
        return None

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        print("[WARNING] GOOGLE_CLOUD_PROJECT environment variable not set.")
        return None

    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"

    try:
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"[ERROR] Failed to access secret {secret_id}: {e}")
        return None