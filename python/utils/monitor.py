# python/utils/monitor.py
import os
import time
from datetime import datetime
from datetime import time as dt_time

import psutil
import psycopg2
from psycopg2 import Error as PgError

from python.config import config
from python.utils.logger import get_logger

logger = get_logger("monitor", category="system")


# --- 計測対象: API呼び出し回数をトラッキング ---
api_call_count = 0


def is_market_open() -> bool:
    """
    現在時刻が日本の証券取引所の取引時間内であるかを確認する。
    東京証券取引所の取引時間は通常、午前9:00から午前11:30、午後12:30から午後15:00。
    土日祝日は閉場。
    """
    now = datetime.now()
    # 土日チェック
    if now.weekday() >= 5:  # 土曜日(5)または日曜日(6)
        return False

    # 祝日チェック (簡易版: ここでは祝日リストは考慮しない)
    # TODO: 祝日を考慮する場合は、日本の祝日リストを取得してチェックするロジックを追加

    # 取引時間チェック
    market_start_morning = dt_time(9, 0, 0)
    market_end_morning = dt_time(11, 30, 0)
    market_start_afternoon = dt_time(12, 30, 0)
    market_end_afternoon = dt_time(15, 0, 0)

    current_time = now.time()

    if (market_start_morning <= current_time <= market_end_morning) or (
        market_start_afternoon <= current_time <= market_end_afternoon
    ):
        return True
    return False


def count_api_call():
    """API呼び出しが行われるたびに呼び出す"""
    global api_call_count
    api_call_count += 1


def get_db_size():
    """PostgreSQL DBのサイズ（MB）"""
    conn = None
    try:
        db_config = config.get_db_config()
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        cur.execute(f"SELECT pg_database_size('{db_config['database']}')")
        size_bytes = cur.fetchone()[0]
        return size_bytes / (1024 * 1024)  # MB
    except PgError as e:
        logger.error(f"データベースサイズ取得エラー: {e}")
        return 0
    finally:
        if conn:
            conn.close()


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
