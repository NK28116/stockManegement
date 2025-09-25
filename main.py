"""
ポートフォリオ管理メインスクリプト
日次 / 週次 / 月次 / 年次タスクをコマンドで実行
"""

import sys
import threading
import time
from datetime import datetime
from datetime import time as dt_time

import jpholiday  # 祝日判定ライブラリ
import pandas as pd

import python.analysis.data_collector
from python.analysis.portfolio_analyzer import PortfolioAnalyzer
from python.config import config
from python.db import dump_csv
from python.trading import every_stock_buy_and_sell_timing
from python.utils.logger import get_logger
from python.utils.monitor import log_resource_usage  # monitorタスク用
from python.utils.report import send_daily_report, send_monthly_report
from python.visualization import generate_all_charts
from python.watch.analyze import (
    analyze_daily_data as run_analyze_daily_data,  # 名前衝突を避けるためエイリアス
)
from python.watch.dailyAggregator import aggregate_intraday_to_daily
from python.watch.watch import run_once_with_crash_check  # watchタスク用

logger = get_logger("main_task", category="task")

analyzer = PortfolioAnalyzer()


def run_daily_task():
    logger.info("=== 日次タスク開始 ===")
    # 1. 日足データ集計
    today_str = datetime.now().strftime("%Y-%m-%d")
    aggregate_intraday_to_daily(today_str)

    # 2. 全銘柄売買タイミング分析 (直近1ヶ月)
    every_stock_buy_and_sell_timing.run_analysis(period="1mo")

    # 3. 全銘柄チャート一括生成
    generate_all_charts.main(period="3mo")  # 日次レポート用として3ヶ月期間を指定

    # 4. 日次レポートのSlack通知
    send_daily_report()

    # 5. 全銘柄の急落検知とテクニカル指標に基づく警告
    try:
        stock_df = pd.read_csv(config.codes_path)
        codes = stock_df["code"].tolist()
        logger.info(f"急落検知対象銘柄数: {len(codes)}")
        for code in codes:
            run_analyze_daily_data(code)
    except Exception as e:
        logger.error(f"急落検知処理中にエラーが発生しました: {e}")

    logger.info("=== 日次タスク完了 ===")


def run_weekly_task():
    logger.info("=== 週次タスク開始 ===")
    # 1. 全銘柄売買タイミング分析 (直近3ヶ月)
    every_stock_buy_and_sell_timing.run_analysis(period="3mo")

    # 2. ポートフォリオ分析
    analyzer.analyze_portfolio()

    # 3. 週次レポートのSlack通知 (analyzer.analyze_portfolio()内で既に呼び出されるため、ここでは不要)
    # send_weekly_report()

    logger.info("=== 週次タスク完了 ===")


def run_monthly_task():
    logger.info("=== 月次タスク開始 ===")
    # 1. 四半期データ収集・分析
    python.analysis.data_collector.main()

    # 2. 全銘柄売買タイミング分析 (直近6ヶ月)
    every_stock_buy_and_sell_timing.run_analysis(period="6mo")

    # 3. 月次レポートのSlack通知
    send_monthly_report()
    logger.info("=== 月次タスク完了 ===")


def run_yearly_task():
    logger.info("=== 年次タスク開始 ===")
    # 1. 全銘柄売買タイミング分析 (直近1年)
    every_stock_buy_and_sell_timing.run_analysis(period="1y")

    # 2. my_stock.dbをアーカイブ
    dump_csv.main()

    logger.info("=== 年次タスク完了 ===")


def is_market_open(current_datetime: datetime) -> bool:
    """日本市場が開いているか判定する (土日祝日、時間帯を考慮)"""
    # 土日判定
    if current_datetime.weekday() >= 5:  # 0=月, 5=土, 6=日
        return False

    # 祝日判定
    if jpholiday.is_holiday(current_datetime.date()):
        return False

    current_time = current_datetime.time()
    # 前場: 9:00 - 11:30
    morning_open = dt_time(9, 0)
    morning_close = dt_time(11, 30)
    # 後場: 12:30 - 15:00
    afternoon_open = dt_time(12, 30)
    afternoon_close = dt_time(15, 0)

    if (morning_open <= current_time <= morning_close) or (afternoon_open <= current_time <= afternoon_close):
        return True
    return False


def watch_task():
    """市場開閉に合わせて株価を監視するタスク"""
    logger.info("=== watchタスク開始 ===")
    while True:
        now = datetime.now()
        if is_market_open(now):
            logger.info("市場開場中: 株価監視を実行します。")
            run_once_with_crash_check()  # 分足取得と急落検知
            time.sleep(config.watch_interval_seconds)  # configで監視間隔を設定できるようにする
        else:
            logger.info("市場閉場中: 次の開場まで待機します。")
            time.sleep(60)  # 1分ごとに市場開閉をチェック


def analyze_background_task():
    """バックグラウンドで日足データを分析し、急落を知らせるタスク"""
    logger.info("=== analyzeバックグラウンドタスク開始 ===")
    stock_df = pd.read_csv(config.codes_path)
    codes = stock_df["code"].tolist()
    while True:
        logger.info("日足データ分析を実行します。")
        for code in codes:
            run_analyze_daily_data(code)
        time.sleep(config.analyze_interval_seconds)  # configで分析間隔を設定できるようにする


def run_always_mode():
    logger.info("=== alwaysモード開始: バックグラウンドタスクを起動します ===")

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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("実行モードを指定してください: daily / weekly / monthly / yearly / always")
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
    else:
        logger.error("不明なモードです: daily / weekly / monthly / yearly / always を指定してください")
        sys.exit(1)
