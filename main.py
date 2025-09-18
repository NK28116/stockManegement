"""
ポートフォリオ管理メインスクリプト
日次 / 週次 / 月次 / 年次タスクをコマンドで実行
"""

import sys

from python.analysis.portfolio_analyzer import PortfolioAnalyzer
from python.db import dump_csv
from python.trading import every_stock_buy_and_sell_timing
from python.utils.logger import get_logger
from python.utils.report import send_daily_report, send_monthly_report
from python.visualization import generate_all_charts

logger = get_logger("main_task", category="task")

analyzer = PortfolioAnalyzer()


def run_daily_task():
    logger.info("=== 日次タスク開始 ===")
    # 1. 全銘柄の売買タイミング分析とレポート保存
    every_stock_buy_and_sell_timing.run()

    # 2. 日次レポートのSlack通知
    send_daily_report()
    logger.info("=== 日次タスク完了 ===")


def run_weekly_task():
    logger.info("=== 週次タスク開始 ===")
    # 日次タスクを実行
    run_daily_task()

    # 1. ポートフォリオ全体の分析と週次レポートのSlack通知
    analyzer.analyze_portfolio()  # この中でsend_weekly_reportが呼ばれる

    # 2. 全銘柄のチャートを生成
    generate_all_charts.main()

    # 3. 週次レポートのSlack通知（analyzer.analyze_portfolio()内で既に呼び出されるため、ここでは不要）
    logger.info("=== 週次タスク完了 ===")


def run_monthly_task():
    logger.info("=== 月次タスク開始 ===")
    # 週次タスクを実行
    run_weekly_task()

    # 1. 月次レポートのSlack通知
    send_monthly_report()
    logger.info("=== 月次タスク完了 ===")


def run_yearly_task():
    logger.info("=== 年次タスク開始 ===")

    # 1. 月次タスクまで実行
    run_monthly_task()

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
