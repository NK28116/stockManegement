import logging
from datetime import datetime

from python.config import config

__all__ = ["get_logger"]


def get_logger(module_name: str, category: str = "general") -> logging.Logger:
    """
    ログをカテゴリ別・モジュール別に管理
    出力先: ./log/{category}/{module_name}/{YYYY-MM-DD}.log
    """
    # プロジェクトルートを基準にログフォルダを作成
    log_dir = config.log_dir / category / module_name
    log_dir.mkdir(parents=True, exist_ok=True)

    # ログファイル名（1日ごとにローテーション）
    log_file = log_dir / (f"{datetime.now().strftime('%Y-%m-%d')}.log")

    logger = logging.getLogger(f"{category}.{module_name}")
    logger.setLevel(logging.INFO)
    logger.propagate = False  # 親ロガーへの伝播を停止

    # ロガーにハンドラが設定されていない場合のみ追加
    if not logger.handlers:
        # ファイル出力
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

        # コンソール出力
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

        # ハンドラ登録
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
