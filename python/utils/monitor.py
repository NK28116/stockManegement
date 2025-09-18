# python/utils/monitor.py
import os
import time
import psutil


from python.config import config
from python.utils.logger import get_logger

logger = get_logger("monitor", category="system")

DB_PATH = config.db_path

# --- 計測対象: API呼び出し回数をトラッキング ---
api_call_count = 0


def count_api_call():
    """API呼び出しが行われるたびに呼び出す"""
    global api_call_count
    api_call_count += 1


def get_db_size():
    """SQLite DBファイルのサイズ（MB）"""
    if os.path.exists(DB_PATH):
        return os.path.getsize(DB_PATH) / (1024 * 1024)  # MB
    return 0


def log_resource_usage(interval=60):
    """
    定期的にCPU/メモリ/DBサイズ/API回数をログ出力する
    :param interval: 計測間隔（秒）
    """
    process = psutil.Process(os.getpid())

    while True:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_usage = process.memory_info().rss / (1024 * 1024)  # MB
        db_size = get_db_size()

        logger.info(
            "リソース使用状況 | CPU: %.1f%% | MEM: %.1fMB | DB: %.2fMB | API Calls: %d",
            cpu_percent,
            memory_usage,
            db_size,
            api_call_count,
        )

        time.sleep(interval)
