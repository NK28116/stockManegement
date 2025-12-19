import logging
import os
from datetime import datetime

# Try to import Google Cloud Logging
try:
    import google.cloud.logging
    from google.cloud.logging.handlers import CloudLoggingHandler

    CLOUD_LOGGING_AVAILABLE = True
except ImportError:
    CLOUD_LOGGING_AVAILABLE = False

from python.config import config

__all__ = ["get_logger"]


def get_logger(module_name: str, category: str = "general") -> logging.Logger:
    """
    ログをカテゴリ別・モジュール別に管理
    出力先:
      - Local: ./log/{category}/{module_name}/{YYYY-MM-DD}.log
      - Cloud: Cloud Logging (if GCP environment detected)
    """

    # Cloud Run 等の環境判定 (簡易的)
    is_cloud_env = (
        bool(os.getenv("K_SERVICE") or os.getenv("GOOGLE_CLOUD_PROJECT"))
        and CLOUD_LOGGING_AVAILABLE
    )

    logger = logging.getLogger(f"{category}.{module_name}")
    logger.setLevel(logging.INFO)
    logger.propagate = False  # 親ロガーへの伝播を停止

    # ロガーにハンドラが設定されていない場合のみ追加
    if not logger.handlers:

        # 1. Cloud Logging Handler (for Cloud Environment)
        if is_cloud_env:
            try:
                client = google.cloud.logging.Client()
                cloud_handler = CloudLoggingHandler(
                    client, name=f"{category}.{module_name}"
                )
                logger.addHandler(cloud_handler)
                # Cloud Loggingの場合は標準出力にも出しておくと便利（コンテナログとして拾われる）
                # ただしCloudLoggingHandlerが直接送るので、重複を避けるならStreamHandlerは不要かもしれないが
                # Cloud Runの標準ログ収集と重複しないように調整が必要。
                # ここでは明示的なCloud Logging転送を行うため、StreamHandlerは追加しない手もあるが、
                # アプリケーションログとして見やすくするためにConsoleも残すことが多い。
                # いったんConsoleも残す。
            except Exception as e:
                print(f"[WARNING] Failed to setup Cloud Logging: {e}")

        # 2. Local File & Console Handler (Default)
        # Cloud環境でもバックアップとしてConsoleには出す

        # プロジェクトルートを基準にログフォルダを作成 (Localのみ)
        if not is_cloud_env:
            log_dir = config.log_dir / category / module_name
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / (f"{datetime.now().strftime('%Y-%m-%d')}.log")

            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(levelname)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M",
                )
            )
            logger.addHandler(file_handler)

        # コンソール出力 (共通)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M"
            )
        )
        logger.addHandler(console_handler)

    return logger
