import os
from typing import Optional

try:
    from google.api_core.exceptions import GoogleAPICallError
    from google.cloud import secretmanager

    SECRET_MANAGER_AVAILABLE = True
except ImportError:
    SECRET_MANAGER_AVAILABLE = False


class SecretManagerClient:
    """
    Client for accessing Google Cloud Secret Manager.
    Falls back to environment variables if Secret Manager is not available or configured.
    """

    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.client = None

        if SECRET_MANAGER_AVAILABLE and self.project_id:
            try:
                self.client = secretmanager.SecretManagerServiceClient()
            except Exception as e:
                print(f"[WARNING] Failed to initialize SecretManagerServiceClient: {e}")
        elif not max:
            # Just logging for awareness, not necessarily an error in local dev
            pass

    def get_secret(
        self, secret_id: str, default: Optional[str] = None
    ) -> Optional[str]:
        """
        Retrieves a secret.
        1. Tries to fetch from Secret Manager (if client is active).
           - Assumes secret name format: projects/{project_id}/secrets/{secret_id}/versions/latest
        2. Falls back to environment variable (os.getenv(secret_id)).
        3. Returns default if neither is found.
        """

        # 1. Try Secret Manager
        if self.client and self.project_id:
            try:
                name = f"projects/{self.project_id}/secrets/{secret_id}/versions/latest"
                response = self.client.access_secret_version(request={"name": name})
                secret_value = response.payload.data.decode("UTF-8")
                return secret_value
            except GoogleAPICallError:
                # Secret might not exist or permission denied
                pass
            except Exception as e:
                print(f"[WARNING] Unexpected error fetching secret {secret_id}: {e}")

        # 2. Fallback to Environment Variable
        env_value = os.getenv(secret_id)
        if env_value is not None:
            return env_value

        # 3. Default
        return default


# Global instance
secret_manager = SecretManagerClient()
