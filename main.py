"""
ポートフォリオ管理メインスクリプト
日次 / 週次 / 月次 / 年次タスクをコマンドで実行
"""

import os
import shutil
import sys
import threading
import time
from datetime import datetime
from datetime import time as dt_time
from datetime import timedelta
from pathlib import Path

import jpholiday  # 祝日判定ライブラリ
import pandas as pd
import psutil  # run_always_test_taskで必要
from dotenv import load_dotenv

import python.analysis.data_collector
from python.analysis.portfolio_analyzer import PortfolioAnalyzer
from python.config import config
from python.db import dump_csv
from python.trading import every_stock_buy_and_sell_timing
from python.trading.trading_rules import generate_trading_report, ImprovedTradingRules # generate_trading_report と ImprovedTradingRules を追加
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
    send_weekly_report,
    send_monthly_report,
    send_startup_report,
)
from python.visualization import generate_all_charts
from python.watch.analyze import analyze_daily_data as run_analyze_daily_data
from python.watch.analyze import analyze_minute_data as run_analyze_intraday_data
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
        send_daily_morning_report(is_test_mode=is_test_mode)
    else:
        logger.info("=== 日次タスク: 市場閉場後モード ===")
        # 1. 日足データ集計
        today_str = datetime.now().strftime("%Y-%m-%d")
        # テストモードでは集計処理は実行するが、永続的な保存は行わない（aggregate_intraday_to_dailyの内部実装による）
        aggregate_intraday_to_daily(today_str, is_test_mode=is_test_mode)
        logger.info("日足データ集計が実行されました。")

        # 2. 全銘柄売買タイミング分析 (直近1ヶ月)
        every_stock_buy_and_sell_timing.run_analysis(period="1mo", is_test_mode=is_test_mode)
        logger.info("全銘柄売買タイミング分析が実行されました。")

        # 3. 全銘柄チャート一括生成
        generate_all_charts.main(period="1mo", is_test_mode=is_test_mode)  # 日次レポート用として3ヶ月期間を指定
        logger.info("全銘柄チャート一括生成が実行されました。")

        # 4. 日次モニターレポートのSlack通知 (市場開場前)
        send_daily_evening_report(is_test_mode=is_test_mode)

        # 5. 全銘柄の急落検知とテクニカル指標に基づく警告
        try:
            stock_df = pd.read_csv(config.codes_path)
            for index, row in stock_df.iterrows():
                code = row["code"]
                name = row["name"]
                run_analyze_daily_data(code, name, is_test_mode=is_test_mode)
            logger.info("全銘柄の急落検知とテクニカル指標に基づく警告が実行されました。")
        except Exception as e:
            logger.error(f"急落検知処理中にエラーが発生しました: {e}")

    logger.info(f"=== 日次タスク完了 (テストモード: {is_test_mode}) ===")


def run_weekly_task(is_test_mode: bool = False):
    logger.info(f"=== 週次タスク開始 (テストモード: {is_test_mode}) ===")
    # 1. 全銘柄売買タイミング分析 (直近3ヶ月)
    every_stock_buy_and_sell_timing.run_analysis(period="3mo", is_test_mode=is_test_mode)
    logger.info("\n 全銘柄売買タイミング分析 (週次) が実行されました。 \n")
    generate_all_charts.main(period="3mo", is_test_mode=is_test_mode)  # 週次レポート用として3ヶ月期間を指定
    logger.info("\n 全銘柄チャート一括生成 (週次) が実行されました。\n")

    # 2. ポートフォリオ分析
    analyzer.analyze_portfolio(is_test_mode=is_test_mode)
    logger.info("ポートフォリオ分析が実行されました。")

    # 3. 週次レポートのSlack通知 (analyzer.analyze_portfolio()内で既に呼び出されるため、ここでは不要)
    # analyzer.analyze_portfolio()内で既に呼び出されるため、ここでは不要
    send_weekly_report(is_test_mode=is_test_mode)
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

    # 3. トレーディングルール見直しレポート生成
    # ポートフォリオ内の全銘柄のデータを取得し、ImprovedTradingRulesで分析
    all_stocks_df = pd.read_csv(config.codes_path)
    all_trades = []
    for _, row in all_stocks_df.iterrows():
        code = row["code"]
        df_stock = analyzer.fetch_stock_data(code, period="6mo") # 6ヶ月分のデータで分析
        if df_stock is not None and not df_stock.empty:
            rules = ImprovedTradingRules() # ImprovedTradingRulesをインポートする必要がある
            trades_for_stock = rules.analyze_with_improved_rules(df_stock)
            all_trades.extend(trades_for_stock)

    # 全銘柄の取引結果をまとめてパフォーマンス指標を計算
    # ImprovedTradingRulesのインスタンスを別途作成して使用
    temp_rules_instance = ImprovedTradingRules()
    overall_metrics = temp_rules_instance.calculate_performance_metrics(all_trades)
    comparison_data = {"new_rules": {"metrics": overall_metrics}}
    generate_trading_report(comparison_data, is_test_mode=is_test_mode)
    logger.info("トレーディングルール見直しレポートが生成されました。")

    # 4. 月次レポートのSlack通知
    send_monthly_report(is_test_mode=is_test_mode)
    logger.info(f"=== 月次タスク完了 (テストモード: {is_test_mode}) ===")


def run_yearly_task():
    logger.info("=== 年次タスク開始 ===")
    # 1. 全銘柄売買タイミング分析 (直近1年)
    every_stock_buy_and_sell_timing.run_analysis(period="1y")

    # 2. my_stock.dbをアーカイブ
    dump_csv.main()

    logger.info("=== 年次タスク完了 ===")


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
            next_open = get_next_open_datetime(now)
            rest_all_seconds = (next_open - now).total_seconds()

            # 次の開場までの全時間に基づいて待機時間を計算
            total_wait_hours = int(rest_all_seconds // 3600)
            total_wait_minutes = int((rest_all_seconds % 3600) // 60)
            total_wait_seconds = int(rest_all_seconds - total_wait_hours * 3600 - total_wait_minutes * 60)

            logger.info(
                f"市場閉場中: 開場まで{total_wait_hours}時間{total_wait_minutes}分{total_wait_seconds}秒です。"
            )
            time.sleep(rest_all_seconds - 300)


def analyze_intraday_task():
    """市場開場中に15分足を分析して速報アラート"""
    logger.info("=== 分足監視タスク開始 ===")
    stock_df = pd.read_csv(config.codes_path)
    while True:
        if is_market_open():
            for _, row in stock_df.iterrows():
                code, name = row["code"], row["name"]
                run_analyze_intraday_data(code, name)  # 15分足
        else:
            logger.info("市場は閉場中。分足監視は休止。")
        time.sleep(config.watch_interval_seconds)  # 例: 300秒


def analyze_daily_task():
    """終値確定後に日足データを分析"""
    logger.info("=== 日足分析タスク開始 ===")
    stock_df = pd.read_csv(config.codes_path)
    while True:
        now = datetime.now()
        # 平日 15:15 頃に実行（終値確定後を想定）
        if now.weekday() < 5 and now.time() >= dt_time(15, 15):
            for _, row in stock_df.iterrows():
                code, name = row["code"], row["name"]
                run_analyze_daily_data(code, name)  # 日足
            logger.info("日足分析を完了しました。次の日まで待機します。")
            time.sleep(24 * 3600)  # 翌日まで待機
        else:
            time.sleep(600)  # 10分ごとにチェック


def run_always_mode():
    logger.info("=== alwaysモード開始: バックグラウンドタスクを起動します ===")
    send_startup_report(is_test_mode=False)  # 起動確認レポートを送信

    # watchタスク (市場開閉に合わせて株価を監視)
    watch_thread = threading.Thread(target=watch_task, daemon=True)
    watch_thread.start()

    # monitorタスク (リソース使用率の監視)
    monitor_thread = threading.Thread(target=log_resource_usage, args=(config.monitor_interval_seconds,), daemon=True)
    monitor_thread.start()

    # 分足監視スレッド
    intraday_thread = threading.Thread(target=analyze_intraday_task, daemon=True)
    intraday_thread.start()

    # 日足監視スレッド
    daily_thread = threading.Thread(target=analyze_daily_task, daemon=True)
    daily_thread.start()

    logger.info("すべてのバックグラウンドタスクが起動しました。メインスレッドは待機します。")
    # メインスレッドはバックグラウンドタスクが終了しないように待機
    while True:
        time.sleep(1)


def run_always_test_task():

    logger.info("=== always-testモード開始: バックグラウンドタスクを1回実行します ===")
    send_startup_report(is_test_mode=True)  # 起動確認レポートを送信

    logger.info("watchタスク (株価監視) を1回実行します。")
    if is_market_open():
        run_once_with_crash_check(is_test_mode=True)
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
            run_analyze_daily_data(code, name, is_test_mode=True)
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
