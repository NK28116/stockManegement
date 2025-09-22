"""
ポートフォリオ管理メインスクリプト
日次 / 週次 / 月次 / 年次タスクをコマンドで実行
"""

import sys
from datetime import datetime

import python.analysis.data_collector
from python.analysis.portfolio_analyzer import PortfolioAnalyzer
from python.db import dump_csv
from python.trading import every_stock_buy_and_sell_timing
from python.utils.logger import get_logger
from python.utils.report import send_daily_report, send_monthly_report
from python.visualization import generate_all_charts
from python.watch.dailyAggregator import aggregate_intraday_to_daily

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
    generate_all_charts.main()

    # 4. 日次レポートのSlack通知
    send_daily_report()

    # 5. 全銘柄の急落検知とテクニカル指標に基づく警告
    import pandas as pd

    from python.config import config
    from python.watch.analyze import (
        analyze_daily_data as run_analyze_daily_data,  # 名前衝突を避けるためエイリアス
    )

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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("実行モードを指定してください: daily / weekly / monthly / yearly")
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
    else:
        logger.error("不明なモードです: daily / weekly / monthly / yearly を指定してください")
        sys.exit(1)
