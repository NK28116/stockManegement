import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# Try importing GCS client, but don't fail if not present (for local dev without requirements yet)
try:
    from google.cloud import storage
    from google.api_core.exceptions import NotFound

    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False

    # ローカル開発時 (google-cloud 未インストール) のフォールバック。
    # use_gcs は GCS_AVAILABLE が False のとき必ず False になるため、
    # この別名が GCS 分岐で実際に使われることはない。
    class NotFound(Exception):
        pass


class GCSClient:
    """
    Google Cloud Storage Client wrapper.
    If GCS_BUCKET_NAME is set, operations are performed on GCS.
    Otherwise, operations are performed on the local filesystem (data/ directory).
    """

    def __init__(self):
        self.bucket_name = os.getenv("GCS_BUCKET_NAME")
        self.use_gcs = bool(self.bucket_name)
        self.local_data_dir = Path("data")

        if self.use_gcs and not GCS_AVAILABLE:
            print(
                "[WARNING] GCS_BUCKET_NAME is set but google-cloud-storage is not installed. Falling back to local."
            )
            self.use_gcs = False

        if self.use_gcs:
            try:
                self.client = storage.Client()
                self.bucket = self.client.bucket(self.bucket_name)
                print(f"[INFO] GCSClient initialized for bucket: {self.bucket_name}")
            except Exception as e:
                print(
                    f"[ERROR] Failed to initialize GCS client: {e}. Falling back to local."
                )
                self.use_gcs = False
        else:
            print("[INFO] GCSClient initialized in LOCAL mode.")

    def _get_local_path(self, path: str) -> Path:
        """Convert relative path (e.g. 'trading_rules/active.json') to local data path."""
        # Ensure path doesn't start with / to splice correctly
        clean_path = path.lstrip("/")
        return self.local_data_dir / clean_path

    def get_json(self, path: str) -> Optional[Dict[str, Any]]:
        """Download JSON from GCS or read from local."""
        if self.use_gcs:
            # 単一 RPC で取得し、未存在は NotFound 例外で判定する
            # (事前の exists() 呼び出しは RPC を二重化するため行わない)。
            try:
                data_str = self.bucket.blob(path).download_as_text(encoding="utf-8")
                return json.loads(data_str)
            except NotFound:
                return None
            except Exception as e:
                print(f"[ERROR] Failed to download JSON from GCS {path}: {e}")
                return None
        else:
            local_path = self._get_local_path(path)
            if not local_path.exists():
                return None
            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[ERROR] Failed to read local JSON {local_path}: {e}")
                return None

    def save_json(self, path: str, data: Dict[str, Any]) -> None:
        """Upload JSON to GCS or save locally."""
        if self.use_gcs:
            blob = self.bucket.blob(path)
            try:
                blob.upload_from_string(
                    json.dumps(data, indent=2, ensure_ascii=False),
                    content_type="application/json",
                )
                print(f"[INFO] Saved JSON to GCS: gs://{self.bucket_name}/{path}")
            except Exception as e:
                print(f"[ERROR] Failed to upload JSON to GCS {path}: {e}")
                raise e
        else:
            local_path = self._get_local_path(path)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            with open(local_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"[INFO] Saved JSON locally: {local_path}")

    def list_files(self, prefix: str) -> List[str]:
        """List files in a directory (prefix). Returns list of filenames (not full paths)."""
        # prefix e.g. "charts/indicators/"
        file_names = []
        if self.use_gcs:
            # list_blobs(prefix=...)
            # ensure prefix ends with / if it's a dir
            if prefix and not prefix.endswith("/"):
                prefix += "/"

            try:
                blobs = self.bucket.list_blobs(prefix=prefix)
                for blob in blobs:
                    # blob.name is full path like "charts/indicators/foo.png"
                    # We want just "foo.png"
                    if blob.name == prefix:
                        continue  # Skip the directory itself if listed

                    # Extract filename relative to prefix
                    rel_name = blob.name[len(prefix) :]
                    if rel_name:
                        file_names.append(rel_name)
            except Exception as e:
                # GCS の認証/権限/ネットワークエラーで API 全体が 500 にならないよう、
                # 空リストにフォールバックする (呼び出し側は「データなし」として扱う)。
                print(f"[ERROR] Failed to list files from GCS prefix '{prefix}': {e}")
                return []
        else:
            local_dir = self._get_local_path(prefix)
            if local_dir.exists() and local_dir.is_dir():
                for item in local_dir.iterdir():
                    if item.is_file() and not item.name.startswith("."):
                        file_names.append(item.name)

        return sorted(file_names)

    def get_file_content(self, path: str) -> Optional[bytes]:
        """Download binary content (e.g. image) from GCS or local."""
        if self.use_gcs:
            # 単一 RPC で取得し、未存在は NotFound 例外で判定する
            # (画像配信など hot path で exists() による RPC 二重化を避ける)。
            try:
                return self.bucket.blob(path).download_as_bytes()
            except NotFound:
                return None
            except Exception as e:
                print(f"[ERROR] Failed to download file from GCS {path}: {e}")
                return None
        else:
            local_path = self._get_local_path(path)
            if not local_path.exists():
                return None
            try:
                with open(local_path, "rb") as f:
                    return f.read()
            except Exception as e:
                print(f"[ERROR] Failed to read local file {local_path}: {e}")
                return None


# Global instance
gcs = GCSClient()
