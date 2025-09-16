"""
ポートフォリオ管理メインスクリプト
日次 / 週次 / 月次 / 年次タスクをコマンドで実行
"""

import os
import sys
from datetime import datetime, timedelta

from . import every_stock_buy_and_sell_timing
from python.analysis.portfolio_analyzer import PortfolioAnalyzer
from python.db import dump_csv  # 年次タスク用に追加
from python.trading import buy_and_sell_stock
from python.utils.logger import get_logger
from python.visualization import generate_all_charts  # 週次タスク用に追加

# from python.analysis.analyze_my_stock import fetch_stock_data
# from python.visualization.plot_indicators import plot_macd_bollinger # PortfolioAnalyzer内でプロットされるため不要

loggerDaily = get_logger("Daily", category="task")
loggerWeekly = get_logger("Weekly", category="task")
loggerMonthly = get_logger("Monthly", category="task")
loggerYearly = get_logger("Yearly", category="task")
loggerError = get_logger("Error", category="task")

analyzer = PortfolioAnalyzer()


def run_daily_task():
    loggerDaily.info("=== 日次タスク開始 ===")
    analyzer.analyze_portfolio()
    every_stock_buy_and_sell_timing.run()
    loggerDaily.info("=== 日次タスク完了 ===")


def run_weekly_task():
    loggerWeekly.info("=== 週次タスク開始 ===")
    run_daily_task()

    # 1. ポートフォリオ全体の分析
    analyzer.analyze_portfolio(plot=False)  # 週次ではプロットはファイル保存のみ

    # 2. 全銘柄のチャートを生成
    generate_all_charts.main()

    # 3. 保有銘柄の分析
    # analyze_my_stock.main() # analyze_my_stock.py の main は単一銘柄の分析なので、ここでは使わない
    # PortfolioAnalyzer の analyze_portfolio で既に分析結果は保存されているため、
    # analyze_my_stock.py の analyze_stock と save_results を直接呼び出す必要はない。
    # もし個別の銘柄分析が必要な場合は、別途ロジックを追加する。

    loggerWeekly.info("=== 週次タスク完了 ===")


def run_monthly_task():
    loggerMonthly.info("=== 月次タスク開始 ===")
    run_weekly_task()

    loggerMonthly.info("=== 月次タスク完了 ===")


def run_yearly_task():
    loggerYearly.info("=== 年次タスク開始 ===")

    # 1. 月次タスクまで実行
    run_monthly_task()

    loggerYearly.info("=== 年次タスク完了 ===")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        loggerError.error("実行モードを指定してください: daily / weekly / monthly / yearly")
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
        loggerError.error("不明なモードです: daily / weekly / monthly / yearly を指定してください")
        sys.exit(1)
