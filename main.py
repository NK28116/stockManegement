"""
ポートフォリオ管理メインスクリプト
日次 / 週次 / 月次 / 年次タスクをコマンドで実行
"""

from dotenv import load_dotenv

import shutil
import sys
import threading
import time
from datetime import datetime, time as dt_time, timedelta
from pathlib import Path

import jpholiday  # 祝日判定ライブラリ
import pandas as pd
import psutil  # run_always_test_taskで必要
import os

import python.analysis.data_collector
from python.analysis.portfolio_analyzer import PortfolioAnalyzer
from python.config import config
from python.db import dump_csv
from python.trading import every_stock_buy_and_sell_timing
from python.utils.logger import get_logger
from python.utils.monitor import (  # monitorタスク用
    api_call_count,
    get_db_size,
    is_market_open,
    log_resource_usage,
)
from python.utils.report import (
    send_daily_evening_report,
    send_daily_morning_report,
    send_monthly_report,
    send_startup_report,
)
from python.visualization import generate_all_charts
from python.watch.analyze import analyze_daily_data as run_analyze_daily_data
from python.watch.dailyAggregator import aggregate_intraday_to_daily
from python.watch.watch import run_once_with_crash_check  # watchタスク用

load_dotenv()
FLAG_DIR = Path("data/crash_flags")


def clear_old_flags():
    """前日の分足急落フラグを削除"""
    if FLAG_DIR.exists():
        shutil.rmtree(FLAG_DIR)
    FLAG_DIR.mkdir(parents=True, exist_ok=True)


logger = get_logger("main_task", category="task")

analyzer = PortfolioAnalyzer()


def run_daily_task(is_test_mode: bool = False):
    logger.info(f"=== 日次タスク開始 (テストモード: {is_test_mode}) ===")

    # 🚨 日足分析前にフラグをリセット
    clear_old_flags()

    if datetime.now().time() < dt_time(9, 0):
        logger.info("=== 日次タスク: 市場開場前モード ===")
        if not is_test_mode:
            send_daily_morning_report()
        else:
            logger.info("テストモードのため、日次朝レポートの送信はスキップします。")
    else:
        logger.info("=== 日次タスク: 市場閉場後モード ===")
        # 1. 日足データ集計
        today_str = datetime.now().strftime("%Y-%m-%d")
        # テストモードでは集計処理は実行するが、永続的な保存は行わない（aggregate_intraday_to_dailyの内部実装による）
        aggregate_intraday_to_daily(today_str)
        logger.info("日足データ集計が実行されました。")

        # 2. 全銘柄売買タイミング分析 (直近1ヶ月)
        every_stock_buy_and_sell_timing.run_analysis(period="1mo", is_test_mode=is_test_mode)
        logger.info("全銘柄売買タイミング分析が実行されました。")

        # 3. 全銘柄チャート一括生成
        generate_all_charts.main(period="1mo", is_test_mode=is_test_mode)  # 日次レポート用として3ヶ月期間を指定
        logger.info("全銘柄チャート一括生成が実行されました。")

        # 4. 日次モニターレポートのSlack通知 (市場開場前)
        if not is_test_mode:
            send_daily_evening_report()
        else:
            logger.info("テストモードのため、日次夜レポートの送信はスキップします。")

        # 5. 全銘柄の急落検知とテクニカル指標に基づく警告
        try:
            stock_df = pd.read_csv(config.codes_path)
            for index, row in stock_df.iterrows():
                code = row["code"]
                name = row["name"]
                run_analyze_daily_data(code, name)
            logger.info("全銘柄の急落検知とテクニカル指標に基づく警告が実行されました。")
        except Exception as e:
            logger.error(f"急落検知処理中にエラーが発生しました: {e}")

    logger.info(f"=== 日次タスク完了 (テストモード: {is_test_mode}) ===")


def run_weekly_task(is_test_mode: bool = False):
    logger.info(f"=== 週次タスク開始 (テストモード: {is_test_mode}) ===")
    # 1. 全銘柄売買タイミング分析 (直近3ヶ月)
    every_stock_buy_and_sell_timing.run_analysis(period="3mo", is_test_mode=is_test_mode)
    logger.info("全銘柄売買タイミング分析 (週次) が実行されました。")
    generate_all_charts.main(period="3mo", is_test_mode=is_test_mode)  # 週次レポート用として3ヶ月期間を指定
    logger.info("全銘柄チャート一括生成 (週次) が実行されました。")

    # 2. ポートフォリオ分析
    analyzer.analyze_portfolio(is_test_mode=is_test_mode)
    logger.info("ポートフォリオ分析が実行されました。")

    # 3. 週次レポートのSlack通知 (analyzer.analyze_portfolio()内で既に呼び出されるため、ここでは不要)
    if not is_test_mode:
        # send_weekly_report() # analyzer.analyze_portfolio()内で既に呼び出されるため、ここでは不要
        pass
    else:
        logger.info("テストモードのため、週次レポートの送信はスキップします。")

    logger.info(f"=== 週次タスク完了 (テストモード: {is_test_mode}) ===")


def run_monthly_task(is_test_mode: bool = False):
    logger.info(f"=== 月次タスク開始 (テストモード: {is_test_mode}) ===")
    # 1. 四半期データ収集・分析
    python.analysis.data_collector.main(is_test_mode=is_test_mode)
    logger.info("四半期データ収集・分析が実行されました。")

    # 2. 全銘柄売買タイミング分析 (直近6ヶ月)
    every_stock_buy_and_sell_timing.run_analysis(period="6mo", is_test_mode=is_test_mode)
    logger.info("全銘柄売買タイミング分析 (月次) が実行されました。")
    generate_all_charts.main(period="6mo", is_test_mode=is_test_mode)
    logger.info("全銘柄チャート一括生成 (月次) が実行されました。")

    # 3. 月次レポートのSlack通知
    if not is_test_mode:
        send_monthly_report()
    else:
        logger.info("テストモードのため、月次レポートの送信はスキップします。")
    logger.info(f"=== 月次タスク完了 (テストモード: {is_test_mode}) ===")


def run_yearly_task():
    logger.info("=== 年次タスク開始 ===")
    # 1. 全銘柄売買タイミング分析 (直近1年)
    every_stock_buy_and_sell_timing.run_analysis(period="1y")

    # 2. my_stock.dbをアーカイブ
    dump_csv.main()

    logger.info("=== 年次タスク完了 ===")


# main.py 内の is_market_open 関数を削除し、python.utils.monitor.is_market_open を使用
# def is_market_open(current_datetime: datetime) -> bool:
#     """日本市場が開いているか判定する (土日祝日、時間帯を考慮)"""
#     # 土日判定
#     if current_datetime.weekday() >= 5:  # 0=月, 5=土, 6=日
#         return False

#     # 祝日判定
#     if jpholiday.is_holiday(current_datetime.date()):
#         return False

#     current_time = current_datetime.time()
#     # 前場: 9:00 - 11:30
#     morning_open = dt_time(9, 0)
#     morning_close = dt_time(11, 30)
#     # 後場: 12:30 - 15:00
#     afternoon_open = dt_time(12, 30)
#     afternoon_close = dt_time(15, 0)

#     if (morning_open <= current_time <= morning_close) or (afternoon_open <= current_time <= afternoon_close):
#         return True
#     return False


def get_next_open_datetime(now: datetime) -> datetime:
    """次の営業日の9:00を返す（土日祝を考慮）"""
    next_day = now.date()
    while True:
        next_day += timedelta(days=1)
        # 土日 or 祝日はスキップ
        if next_day.weekday() >= 5 or jpholiday.is_holiday(next_day):
            continue
        return datetime.combine(next_day, dt_time(9, 0))


def watch_task():
    """市場開閉に合わせて株価を監視するタスク"""
    logger.info("=== watchタスク開始 ===")
    while True:
        now = datetime.now()
        if is_market_open():  # monitor.py の is_market_open を使用
            logger.info("市場開場中: 株価監視を実行します。")
            run_once_with_crash_check()  # 分足取得と急落検知
            time.sleep(config.watch_interval_seconds)  # configで監視間隔を設定できるようにする
        else:
            next_open = None
            for start_hour in [9, 12]:  # 午前9時と午後12時半の両方をチェック
                if now.time() < dt_time(start_hour, 0):
                    next_open = datetime.combine(now.date(), dt_time(start_hour, 0))
                    break
            if not next_open:
                next_open = get_next_open_datetime(now)

            rest_all_seconds = (next_open - now).total_seconds()

            # 閉場中の待機ロジック
            # 2時間ごとに市場開閉をチェックするように変更
            wait_interval = 2 * 3600  # 2時間 (秒)
            while not is_market_open():  # monitor.py の is_market_open を使用
                now = datetime.now()
                next_open = None
                for start_hour in [9, 12]:
                    if now.time() < dt_time(start_hour, 0):
                        next_open = datetime.combine(now.date(), dt_time(start_hour, 0))
                        break
                if not next_open:
                    next_open = get_next_open_datetime(now)

                rest_all_seconds = (next_open - now).total_seconds()

                # 次の開場までの時間が2時間以上ある場合は、2時間待機
                # そうでない場合は、次の開場までの時間待機
                sleep_duration = min(rest_all_seconds, wait_interval)

                # 次の開場までの全時間に基づいて待機時間を計算
                total_wait_hours = int(rest_all_seconds // 3600)
                total_wait_minutes = int((rest_all_seconds % 3600) // 60)
                total_wait_seconds = int(rest_all_seconds - total_wait_hours * 3600 - total_wait_minutes * 60)

                logger.info(
                    f"市場閉場中: 開場まで{total_wait_hours}時間{total_wait_minutes}分{total_wait_seconds}秒です。"
                )
                time.sleep(sleep_duration)


def analyze_background_task():
    """バックグラウンドで日足データを分析し、急落を知らせるタスク"""
    logger.info("=== analyzeバックグラウンドタスク開始 ===")
    stock_df = pd.read_csv(config.codes_path)
    while True:
        if is_market_open():  # 市場が開いている場合のみ実行
            logger.info("日足データ分析を実行します。")
            # 'code'と'name'カラムが存在することを前提とする
            for index, row in stock_df.iterrows():
                code = row["code"]
                name = row["name"]
                run_analyze_daily_data(code, name)
        else:
            logger.info("市場閉場中: 日足データ分析はスキップします。")
        time.sleep(config.analyze_interval_seconds)  # configで分析間隔を設定できるようにする


def run_always_mode():
    logger.info("=== alwaysモード開始: バックグラウンドタスクを起動します ===")
    send_startup_report()  # 起動確認レポートを送信

    # watchタスク (市場開閉に合わせて株価を監視)
    watch_thread = threading.Thread(target=watch_task, daemon=True)
    watch_thread.start()

    # monitorタスク (リソース使用率の監視)
    monitor_thread = threading.Thread(target=log_resource_usage, args=(config.monitor_interval_seconds,), daemon=True)
    monitor_thread.start()

    # analyzeタスク (急落検知とテクニカル指標に基づく警告)
    analyze_thread = threading.Thread(target=analyze_background_task, daemon=True)
    analyze_thread.start()

    logger.info("すべてのバックグラウンドタスクが起動しました。メインスレッドは待機します。")
    # メインスレッドはバックグラウンドタスクが終了しないように待機
    while True:
        time.sleep(1)


def run_always_test_task():

    logger.info("=== always-testモード開始: バックグラウンドタスクを1回実行します ===")
    send_startup_report()  # 起動確認レポートを送信

    logger.info("watchタスク (株価監視) を1回実行します。")
    if is_market_open():
        run_once_with_crash_check()
    else:
        logger.info("市場閉場中: watchタスクはスキップします。")

    logger.info("monitorタスク (リソース使用率の監視) を1回実行します。")
    process = psutil.Process(os.getpid())
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

    logger.info("analyzeタスク (急落検知とテクニカル指標に基づく警告) を1回実行します。")
    stock_df = pd.read_csv(config.codes_path)
    if is_market_open():
        for index, row in stock_df.iterrows():
            code = row["code"]
            name = row["name"]
            run_analyze_daily_data(code, name)
    else:
        logger.info("市場閉場中: analyzeタスクはスキップします。")

    logger.info("=== always-testモード完了 ===")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error(
            "実行モードを指定してください: \
            daily / weekly / monthly / yearly / always / \
            always-test / daily-test / weekly-test / monthly-test"
        )
        sys.exit(1)

    mode = sys.argv[1].lower()
    if mode == "daily":
        run_daily_task()
    elif mode == "weekly":
        run_weekly_task()
    elif mode == "monthly":
        run_monthly_task()
    elif mode == "yearly":
        run_yearly_task()
    elif mode == "always":
        run_always_mode()
    elif mode == "always-test":
        run_always_test_task()
    elif mode == "daily-test":
        run_daily_task(is_test_mode=True)
    elif mode == "weekly-test":
        run_weekly_task(is_test_mode=True)
    elif mode == "monthly-test":
        run_monthly_task(is_test_mode=True)
    else:
        logger.error(
            "不明なモードです:\
            daily / weekly / monthly / yearly / always / \
            always-test / daily-test / weekly-test / monthly-test \
            を指定してください"
        )
        sys.exit(1)
