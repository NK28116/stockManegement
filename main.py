"""
ポートフォリオ管理メインスクリプト
日次 / 週次 / 月次 / 年次タスクをコマンドで実行
"""

import sys
from pathlib import Path

# プロジェクトルートを追加（インポートの前に必要）
ROOT_DIR = Path(__file__).resolve().parent
sys.path.append(str(ROOT_DIR / "python"))

import logging
from datetime import datetime, timedelta

from analysis.portfolio_analyzer import PortfolioAnalyzer, analyze_portfolio
from visualization.plot_indicators import plot_macd_bollinger
from trading import every_stock_BuySell_timing, buy_and_sell_stock
from db import dump_csv  # 年次タスク用に追加

# --- ログ設定 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_daily_task():
    logger.info("=== 日次タスク開始 ===")
    analyze_portfolio()
    every_stock_BuySell_timing.run()
    logger.info("=== 日次タスク完了 ===")


def run_weekly_task():
    logger.info("=== 週次タスク開始 ===")
    run_daily_task()

    analyzer = PortfolioAnalyzer()
    portfolio_file = "../data/my_stock.csv"
    portfolio = analyzer.load_portfolio_from_file(portfolio_file)
    if portfolio:
        end_date = datetime.today().strftime("%Y-%m-%d")
        start_date = (datetime.today() - timedelta(days=365)).strftime("%Y-%m-%d")
        codes = list(portfolio.keys())
        price_data = analyzer.fetch_historical_data(codes, start_date, end_date)
        returns = analyzer.calculate_returns(price_data)
        metrics = analyzer.calculate_portfolio_metrics(portfolio, returns)
        correlation_matrix = analyzer.calculate_correlation_matrix(returns)
        indicators = analyzer.calculate_technical_indicators(price_data)
        report = analyzer.generate_portfolio_report(
            portfolio, metrics, correlation_matrix, indicators
        )
        analyzer.save_analysis_result(report, filename="weekly_portfolio_report.txt")
        plot_macd_bollinger(price_data, indicators)

    buy_and_sell_stock.evaluate_weekly_trades()
    logger.info("=== 週次タスク完了 ===")


def run_monthly_task():
    logger.info("=== 月次タスク開始 ===")
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
        report = analyzer.generate_portfolio_report(
            portfolio, metrics, correlation_matrix, indicators
        )
        analyzer.save_analysis_result(report, filename="monthly_portfolio_report.txt")
        plot_macd_bollinger(price_data, indicators)

    logger.info("=== 月次タスク完了 ===")


def run_yearly_task():
    logger.info("=== 年次タスク開始 ===")

    # 1. 月次タスクまで実行
    run_monthly_task()

    # 2. DBをCSVにダンプして古いデータ削除
    year = datetime.today().year - 1  # 昨年分を対象
    db_path = "../data/portfolio.db"
    output_dir = "../data/dump"

    try:
        dump_csv.dump_and_cleanup(db_path, output_dir, year)
        logger.info(f"{year} 年のデータをCSVにダンプし、DBから削除しました。")
    except Exception as e:
        logger.error(f"年次ダンプ処理でエラー: {e}")

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