import logging
import os
from datetime import datetime
from pathlib import Path

def get_logger(module_name: str, category: str = "general") -> logging.Logger:
    """
    ログをカテゴリ別・モジュール別に管理
    出力先: ./log/{category}/{module_name}/{YYYY-MM-DD}.log
    """
    # プロジェクトルートを基準にログフォルダを作成
    root_dir = Path(__file__).resolve().parents[2]  # python/ の2つ上がプロジェクトルート
    log_dir = root_dir / "log" / category / module_name
    log_dir.mkdir(parents=True, exist_ok=True)

    # ログファイル名（1日ごとにローテーション）
    log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"

    logger = logging.getLogger(f"{category}.{module_name}")
    logger.setLevel(logging.INFO)

    # 既存ハンドラをクリア（重複防止）
    if logger.hasHandlers():
        logger.handlers.clear()

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