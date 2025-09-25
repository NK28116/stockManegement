# python/analysis/portfolio_analyzer.py
import os
from datetime import datetime
from typing import Dict

import matplotlib.pyplot as plt
import pandas as pd
import psycopg2
import yfinance as yf
from psycopg2 import Error as PgError

from python.analysis.formula_for_analyzer import calculate_technical_indicators
from python.config import config
from python.db.database import get_db_connection
from python.utils.logger import get_logger

logger = get_logger("PortfolioAnalyzer", category="analysis")

RESULT_DIR = config.root_dir / "data"
PLOT_DIR = RESULT_DIR / "plots"
os.makedirs(PLOT_DIR, exist_ok=True)

__all__ = ["PortfolioAnalyzer"]


class PortfolioAnalyzer:
    def __init__(self, result_dir=RESULT_DIR):
        self.result_dir = result_dir
        os.makedirs(self.result_dir, exist_ok=True)

    def get_portfolio(self, portfolio_name="my_stock") -> pd.DataFrame:
        """DBから保有株式情報を全取得"""
        conn = None
        try:
            conn = get_db_connection()
            query = """
            SELECT ph.id, ph.code, s.name, s.sector, ph.quantity, ph.purchase_price, ph.purchase_date
            FROM portfolio_holdings ph
            JOIN stocks s ON ph.code = s.code
            WHERE ph.portfolio_name = %s
            """
            df = pd.read_sql_query(query, conn, params=(portfolio_name,))
            logger.info(f"DBポートフォリオ取得: {portfolio_name} ({len(df)}件)")
            return df
        except PgError as e:
            logger.error(f"DBポートフォリオ取得エラー: {e}")
            return pd.DataFrame()
        finally:
            if conn:
                conn.close()

    def fetch_stock_data(self, ticker: str, period="1y") -> pd.DataFrame:
        """Yahoo Finance から株価データを取得"""
        try:
            logger.info(f"株価データ取得開始: {ticker}")
            stock = yf.Ticker(ticker)
            df = stock.history(period=period)
            if df.empty:
                logger.warning(f"データが取得できませんでした: {ticker}")
            return df
        except Exception as e:
            logger.error(f"株価データ取得エラー: {ticker} - {e}")
            return pd.DataFrame()

    def plot_indicators(self, price_df: pd.DataFrame, indicators: pd.DataFrame, code: str, name: str):
        """株価 + テクニカル指標グラフ描画"""
        if price_df.empty or indicators.empty:
            logger.warning(f"{code}-{name} の描画対象データが空です")
            return

        fig, ax = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

        # 価格 + Bollinger Bands
        ax[0].plot(price_df.index, price_df["Close"], label="Close")
        ax[0].plot(indicators.index, indicators["bb_middle"], label="BB Middle", linestyle="--", color="orange")
        ax[0].plot(indicators.index, indicators["bb_upper"], label="BB Upper", linestyle="--", color="green")
        ax[0].plot(indicators.index, indicators["bb_lower"], label="BB Lower", linestyle="--", color="red")
        ax[0].set_title(f"{code}-{name} Price + Bollinger Bands")
        ax[0].legend()

        # MACD
        ax[1].plot(indicators.index, indicators["macd"], label="MACD", color="blue")
        ax[1].plot(indicators.index, indicators["macd_signal"], label="Signal", color="red")
        ax[1].bar(indicators.index, indicators["macd_dif"], label="MACD Dif", color="gray")
        ax[1].set_title(f"{code}-{name} MACD")
        ax[1].legend()

        plt.tight_layout()
        plot_file = PLOT_DIR / f"{code}-{name}_plot.png"
        fig.savefig(plot_file)
        logger.info(f"{code}-{name} のプロットを保存: {plot_file}")
        plt.close(fig)

    def save_analysis(self, portfolio_df: pd.DataFrame, indicators_dict: Dict[str, pd.DataFrame]):
        """ポートフォリオ分析結果を保存"""
        output_file = self.result_dir / "my_portfolio_analysis.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("ポートフォリオ分析レポート\n")
            f.write("=" * 60 + "\n")
            f.write(f"分析日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"対象銘柄数: {len(portfolio_df)}\n\n")
            f.write("【ポートフォリオ概要】\n")
            total_investment = (portfolio_df["quantity"] * portfolio_df["purchase_price"]).sum()
            f.write(f"総投資額: {int(total_investment)}円\n\n")
            f.write("【銘柄別詳細】\n")
            for _, row in portfolio_df.iterrows():
                f.write(f"{row['code']} ({row['name']})\n")
                f.write(f"  数量: {row['quantity']}株\n")
                f.write(f"  購入価格: {row['purchase_price']}円\n")
                f.write(f"  投資額: {row['quantity']*row['purchase_price']}円\n")
                weight = row["quantity"] * row["purchase_price"] / total_investment * 100
                f.write(f"  ウェイト: {weight:.2f}%\n\n")
        logger.info(f"ポートフォリオ分析結果を保存: {output_file}")

    def analyze_portfolio(self, portfolio_name="my_stock"):
        """ポートフォリオ全体を分析"""
        portfolio_df = self.get_portfolio(portfolio_name)
        if portfolio_df.empty:
            logger.warning("分析対象のポートフォリオがありません")
            return

        indicators_dict = {}
        for _, row in portfolio_df.iterrows():
            code = row["code"]
            name = row["name"]
            price_df = self.fetch_stock_data(code)
            if price_df.empty:
                continue
            indicators = calculate_technical_indicators(price_df)
            indicators_dict[code] = indicators
            self.plot_indicators(price_df, indicators, code, name)

        self.save_analysis(portfolio_df, indicators_dict)
        logger.info("✅ ポートフォリオ分析完了")
        # 週次レポートとしてSlackに通知
        from python.utils.report import send_weekly_report

        send_weekly_report()


if __name__ == "__main__":
    analyzer = PortfolioAnalyzer()
    analyzer.analyze_portfolio()
