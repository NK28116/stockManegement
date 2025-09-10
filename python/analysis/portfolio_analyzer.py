# my_stock.db から保有株式情報を取得し、株価データを取得する
import os
import sqlite3

from datetime import datetime
from typing import List, Optional

import matplotlib.pyplot as plt
import pandas as pd
import ta
import yfinance as yf

from python.config import config
from python.utils.logger import get_logger

logger = get_logger("PortfolioAnalyzer", category="analysis")

DB_PATH = config.db_path
DEFAULT_RESULT_DIR = config.root_dir / "data" / "analyze_my_stock_db"
os.makedirs(DEFAULT_RESULT_DIR, exist_ok=True)


class PortfolioAnalyzer:
    def __init__(self, db_path=DB_PATH, result_dir=DEFAULT_RESULT_DIR):
        self.db_path = db_path
        self.result_dir = result_dir
        os.makedirs(self.result_dir, exist_ok=True)

    def get_portfolio(self, portfolio_name="stock", csv_path=None):
        """保有株式情報を取得（DB優先、CSVがあれば読み込む）"""
        if csv_path and os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            logger.info(f"CSVポートフォリオ読み込み: {csv_path} ({len(df)}件)")
            return df

        query = """
        SELECT ph.id, ph.code, s.name, s.sector, ph.quantity, ph.purchase_price, ph.purchase_date
        FROM portfolio_holdings ph
        JOIN stocks s ON ph.code = s.code
        WHERE ph.portfolio_name = ?
        """
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=(portfolio_name,))
        logger.info(f"DBポートフォリオ取得: {portfolio_name} ({len(df)}件)")
        return df

    def get_stock_prices(self, code):
        """特定銘柄の株価取得"""
        query = """
        SELECT date, open, high, low, close, volume
        FROM stock_prices
        WHERE code = ?
        ORDER BY date
        """
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=(code,))
        if df.empty:
            logger.warning(f"株価データが見つかりません: {code}")
            return df
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
        return df

    def fetch_stock_data(self, ticker: str, period: int) -> Optional[pd.DataFrame]:
        """
        株価データを取得する

        Args:
            ticker: ティッカーシンボル
            period: 取得期間

        Returns:
            DataFrame: 株価データ、エラーの場合はNone
        """
        try:
            logger.info(f"株価データ取得開始: {ticker}")
            stock = yf.Ticker(ticker)
            df = stock.history(period=period)

            if df.empty:
                logger.error(f"データが取得できませんでした: {ticker}")
                return None

            logger.info(f"株価データ取得完了: {ticker} - {len(df)}件")
            return df

        except Exception as e:
            logger.error(f"株価データ取得エラー: {ticker} - {e}")
            return None

    def analyze_stock(self, df: pd.DataFrame) -> List[str]:
        """
        株価データを分析する

        Args:
            df: 株価データ

        Returns:
            List[str]: 分析結果
        """
        try:
            if df is None or df.empty:
                logger.error("分析対象のデータがありません")
                return ["エラー: 分析対象のデータがありません"]

            closes = df["Close"].tolist()
            signals = []

            for i in range(1, len(closes)):
                change = "+" if closes[i] > closes[i - 1] else "-"
                signals.append(change)

            results = []
            buy_price = None  # 買値を記録

            for i in range(1, len(signals)):
                pattern = signals[i - 1] + signals[i]
                # Off-by-one 修正: パターンは signals[i] を含むため、date/price も i+1 を参照
                date = df.index[i + 1].strftime("%Y-%m-%d")
                price = closes[i + 1]

                if pattern == "++" and buy_price is None:
                    # 買いエントリー
                    buy_price = price

                    results.append(f"{date} {price:.2f}円: ++ → 買いエントリー")

                elif pattern == "+-":
                    results.append(f"{date} {price:.2f}円: +- → 次に++または--が出たら売却")

                elif pattern == "--" and buy_price is not None:
                    # 売却
                    diff = price - buy_price
                    results.append(f"{date} {price:.2f}円: -- → 売却（買値 {buy_price:.2f}円 → 損益 {diff:.2f}円）")
                    buy_price = None  # リセット

                elif pattern == "++" and buy_price is not None:
                    results.append(f"{date} {price:.2f}円: ++ → 継続保持中")

                elif pattern == "+-" and buy_price is not None:
                    results.append(f"{date} {price:.2f}円: +- → 継続保持中")

                else:
                    results.append(f"{date} {price:.2f}円: 継続 ({pattern})")

            logger.info(f"分析完了: {len(results)}件の結果")
            return results

        except Exception as e:
            logger.error(f"分析エラー: {e}")
            return [f"エラー: 分析中に問題が発生しました - {e}"]

    def save_results(self, results: List[str], filename="result_my_stock_analysis.txt") -> bool:
        """
        分析結果を保存する

        Args:
            results: 分析結果のリスト

        Returns:
            bool: 保存が成功したかどうか
        """
        output_file = os.path.join(self.result_dir, "analyze_my_stock", filename)
        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"# 分析結果 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")
                for line in results:
                    f.write(line + "\n")

            logger.info(f"結果を {output_file} に保存しました")
            return True

        except Exception as e:
            logger.error(f"結果保存エラー: {e}")
            return False

    def calculate_technical_indicators(self, price_df):
        """テクニカル指標を計算"""
        if price_df.empty:
            return pd.DataFrame()
        indicators = pd.DataFrame(index=price_df.index)
        indicators["Close"] = price_df["close"]

        bb = ta.volatility.BollingerBands(close=price_df["close"], window=20, window_dev=2)
        indicators["bb_middle"] = bb.bollinger_mavg()
        indicators["bb_upper"] = bb.bollinger_hband()
        indicators["bb_lower"] = bb.bollinger_lband()

        macd = ta.trend.MACD(close=price_df["close"])
        indicators["macd"] = macd.macd()
        indicators["macd_signal"] = macd.macd_signal()
        indicators["macd_diff"] = macd.macd_diff()

        return indicators

    def save_analysis(self, portfolio_df, indicators_dict, filename=None):
        """分析結果をテキスト保存"""
        if filename is None:
            filename = f"portfolio_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join(self.result_dir, filename)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("=== Portfolio Holdings ===\n")
                f.write(portfolio_df.to_string(index=False))
                f.write("\n\n=== Technical Indicators ===\n")
                for code, ind in indicators_dict.items():
                    f.write(f"\n--- {code} ---\n")
                    f.write(ind.tail(5).to_string())
            logger.info(f"分析結果を保存: {filepath}")
        except Exception as e:
            logger.error(f"分析結果の保存に失敗しました: {e}")

    def plot_indicators(self, price_df, indicators, code, show=True):
        """株価 + テクニカル指標グラフ描画"""
        if price_df.empty or indicators.empty:
            logger.warning(f"{code} の描画対象データが空です")
            return

        fig, ax = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

        ax[0].plot(price_df.index, price_df["close"], label="Close")
        ax[0].plot(
            indicators.index,
            indicators["bb_middle"],
            label="BB Middle",
            linestyle="--",
            color="orange",
        )
        ax[0].plot(
            indicators.index,
            indicators["bb_upper"],
            label="BB Upper",
            linestyle="--",
            color="green",
        )
        ax[0].plot(
            indicators.index,
            indicators["bb_lower"],
            label="BB Lower",
            linestyle="--",
            color="red",
        )
        ax[0].set_title(f"{code} Price + Bollinger Bands")
        ax[0].legend()

        ax[1].plot(indicators.index, indicators["macd"], label="MACD", color="blue")
        ax[1].plot(indicators.index, indicators["macd_signal"], label="Signal", color="red")
        ax[1].bar(indicators.index, indicators["macd_diff"], label="MACD Diff", color="gray")
        ax[1].set_title(f"{code} MACD")
        ax[1].legend()

        plt.tight_layout()
        if show:
            plt.show()
        else:
            plot_file = os.path.join(self.result_dir, f"{code}_plot.png")
            fig.savefig(plot_file)
            logger.info(f"{code} のプロットを保存: {plot_file}")
        plt.close(fig)

    def analyze_portfolio(self, portfolio_name="my_stock", csv_path=None, plot=True):
        """ポートフォリオ全体を分析"""
        portfolio_df = self.get_portfolio(portfolio_name=portfolio_name, csv_path=csv_path)
        if portfolio_df.empty:
            logger.warning("分析対象のポートフォリオがありません")
            return

        indicators_dict = {}
        for _, row in portfolio_df.iterrows():
            code = row["code"]
            price_df = self.get_stock_prices(code)
            if price_df.empty:
                continue
            indicators = self.calculate_technical_indicators(price_df)
            indicators_dict[code] = indicators
            self.plot_indicators(price_df, indicators, code, show=plot)

        self.save_analysis(portfolio_df, indicators_dict)
        logger.info("✅ ポートフォリオ分析完了")


if __name__ == "__main__":
    analyzer = PortfolioAnalyzer()
    analyzer.analyze_portfolio(config.codes_path)
