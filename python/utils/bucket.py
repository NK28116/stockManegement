"""GCS バケット名の取得。

バケット名はリポジトリへ書かず、環境変数 (または .env) の GCS_BUCKET_NAME で指定する。
未設定のまま本番用バケットへ黙って書き込まないよう、見つからなければ例外にする。
"""

import os

from dotenv import load_dotenv

__all__ = ["get_bucket_name"]


def get_bucket_name() -> str:
    load_dotenv()  # 既に設定済みの環境変数は上書きしない
    name = (os.getenv("GCS_BUCKET_NAME") or "").strip()
    if not name:
        raise RuntimeError(
            "GCS_BUCKET_NAME が設定されていません。環境変数または .env で指定してください"
        )
    return name
