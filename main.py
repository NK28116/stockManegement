"""
ポートフォリオ管理メインスクリプト
日次 / 週次 / 月次 / 年次タスクをコマンドで実行
"""

import os
import sys

from datetime import datetime, timedelta

from python.analysis.portfolio_analyzer import PortfolioAnalyzer
from python.db import dump_csv  # 年次タスク用に追加
from python.trading import buy_and_sell_stock, every_stock_BuySell_timing
from python.utils.logger import get_logger

# from python.analysis.analyze_my_stock import fetch_stock_data
from python.visualization.plot_indicators import plot_macd_bollinger

loggerDaily = get_logger("Daily", category="task")
loggerWeekly = get_logger("Weekly", category="task")
loggerMonthly = get_logger("Monthly", category="task")
loggerYearly = get_logger("Yearly", category="task")
loggerError = get_logger("Error", category="task")

analyzer = PortfolioAnalyzer()


def run_daily_task():
    loggerDaily.info("=== 日次タスク開始 ===")
    analyzer.analyze_portfolio()
    every_stock_BuySell_timing.run()
    loggerDaily.info("=== 日次タスク完了 ===")


def run_weekly_task():
    loggerWeekly.info("=== 週次タスク開始 ===")
    run_daily_task()

    portfolio_file = os.path.join(os.path.dirname(__file__), "data/my_stock.csv")
    portfolio = analyzer.get_portfolio(csv_path=portfolio_file)

    if not portfolio.empty:
        end_date = datetime.today().strftime("%Y-%m-%d")
        start_date = (datetime.today() - timedelta(days=365)).strftime("%Y-%m-%d")
        codes = list(portfolio["code"])
        # tickerをperiod日分取得
        price_data = analyzer.fetch_stock_data(codes, period=7)

        returns = analyzer.calculate_returns(price_data)
        metrics = analyzer.calculate_portfolio_metrics(portfolio, returns)
        correlation_matrix = analyzer.calculate_correlation_matrix(returns)

        indicators = analyzer.calculate_technical_indicators(price_data)
        #
        report = analyzer.generate_portfolio_report(portfolio, metrics, correlation_matrix, indicators)
        analyzer.save_analysis(report, filename="weekly_portfolio_report.txt")
        plot_macd_bollinger(price_data, indicators)
    else:
        loggerWeekly.warning(f"ポートフォリオデータが空です: {portfolio_file}")

    buy_and_sell_stock.evaluate_weekly_trades()
    loggerWeekly.info("=== 週次タスク完了 ===")


def run_monthly_task():
    loggerMonthly.info("=== 月次タスク開始 ===")
    run_weekly_task()

    buy_and_sell_stock.run_backtest()

    analyzer = PortfolioAnalyzer()
    portfolio_file = "../data/my_stock.csv"
    portfolio = analyzer.load_portfolio_from_file(portfolio_file)
    if portfolio:
        end_date = datetime.today().strftime("%Y-%m-%d")
        start_date = (datetime.today() - timedelta(days=365 * 3)).strftime("%Y-%m-%d")
        codes = list(portfolio.keys())
        price_data = analyzer.fetch_historical_data(codes, start_date, end_date)
        returns = analyzer.calculate_returns(price_data)
        metrics = analyzer.calculate_portfolio_metrics(portfolio, returns)
        correlation_matrix = analyzer.calculate_correlation_matrix(returns)
        indicators = analyzer.calculate_technical_indicators(price_data)
        report = analyzer.generate_portfolio_report(portfolio, metrics, correlation_matrix, indicators)
        analyzer.save_analysis_result(report, filename="monthly_portfolio_report.txt")
        plot_macd_bollinger(price_data, indicators)

    loggerMonthly.info("=== 月次タスク完了 ===")


def run_yearly_task():
    loggerYearly.info("=== 年次タスク開始 ===")

    # 1. 月次タスクまで実行
    run_monthly_task()

    # 2. DBをCSVにダンプして古いデータ削除
    year = datetime.today().year - 1  # 昨年分を対象
    db_path = "../data/portfolio.db"
    output_dir = "../data/dump"

    try:
        dump_csv.dump_and_cleanup(db_path, output_dir, year)
        loggerYearly.info(f"{year} 年のデータをCSVにダンプし、DBから削除しました。")
    except Exception as e:
        loggerYearly.error(f"年次ダンプ処理でエラー: {e}")

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
