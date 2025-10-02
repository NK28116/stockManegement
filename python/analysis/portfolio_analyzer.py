# python/analysis/portfolio_analyzer.py
import os
from datetime import datetime, timedelta
from typing import Dict

import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf
from psycopg2 import Error as PgError

from python.analysis.formula_for_analyzer import calculate_technical_indicators
from python.config import config
from python.db.database import get_db_connection
from python.utils.logger import get_logger

logger = get_logger("PortfolioAnalyzer", category="analysis")

RESULT_DIR = config.root_dir / "data"
PLOT_DIR = RESULT_DIR / "plots"
# os.makedirs(PLOT_DIR, exist_ok=True) # is_test_modeで制御するためコメントアウト

__all__ = ["PortfolioAnalyzer"]


class PortfolioAnalyzer:
    def __init__(self, result_dir=RESULT_DIR, is_test_mode: bool = False):
        self.result_dir = result_dir
        self.is_test_mode = is_test_mode
        if not self.is_test_mode:
            os.makedirs(self.result_dir, exist_ok=True)
            os.makedirs(PLOT_DIR, exist_ok=True)

    def get_portfolio(self, portfolio_name="my_stock") -> pd.DataFrame:
        """DBから保有株式情報を全取得"""
        conn = None
        try:
            conn = get_db_connection()
            query = """
            SELECT ph.id, ph.code, s.name, s.purpose, ph.quantity, ph.purchase_price, ph.purchase_date
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
        if not self.is_test_mode:
            plot_file = PLOT_DIR / f"{code}-{name}_plot.png"
            fig.savefig(plot_file)
            logger.info(f"{code}-{name} のプロットを保存: {plot_file}")
        else:
            logger.info(f"テストモードのため、{code}-{name} のプロット保存はスキップします。")
        plt.close(fig)

    def save_analysis(self, portfolio_df: pd.DataFrame, indicators_dict: Dict[str, pd.DataFrame]):
        """ポートフォリオ分析結果を保存"""
        output_file = self.result_dir / "my_portfolio_analysis.txt"

        if self.is_test_mode:
            logger.info("テストモードのため、ポートフォリオ分析結果の保存はスキップします。")
            report_content = self._generate_analysis_report_content(portfolio_df, indicators_dict)
            logger.debug(f"ポートフォリオ分析レポート (テストモード):\n{report_content}")
            return

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# -*- coding: utf-8 -*-\n\n") # 文字コード宣言を追加
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

    def _generate_analysis_report_content(
        self, portfolio_df: pd.DataFrame, indicators_dict: Dict[str, pd.DataFrame]
    ) -> str:
        """分析レポートの内容を生成するヘルパー関数"""
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("ポートフォリオ分析レポート")
        report_lines.append("=" * 60)
        report_lines.append(f"分析日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"対象銘柄数: {len(portfolio_df)}\n")
        report_lines.append("【ポートフォリオ概要】")
        total_investment = (portfolio_df["quantity"] * portfolio_df["purchase_price"]).sum()
        report_lines.append(f"総投資額: {int(total_investment)}円\n")
        report_lines.append("【銘柄別詳細】")
        for _, row in portfolio_df.iterrows():
            report_lines.append(f"{row['code']} ({row['name']})")
            report_lines.append(f"  数量: {row['quantity']}株")
            report_lines.append(f"  購入価格: {row['purchase_price']}円")
            report_lines.append(f"  投資額: {row['quantity']*row['purchase_price']}円")
            weight = row["quantity"] * row["purchase_price"] / total_investment * 100
            report_lines.append(f"  ウェイト: {weight:.2f}%\n")
        return "\n".join(report_lines)

    def analyze_portfolio(self, portfolio_name="my_stock", is_test_mode: bool = False):
        """ポートフォリオ全体を分析"""
        self.is_test_mode = is_test_mode  # インスタンス変数に設定
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
        if not self.is_test_mode:
            from python.utils.report import send_weekly_report

            send_weekly_report()
        else:
            logger.info("テストモードのため、週次レポートのSlack通知はスキップします。")

    def _get_transactions(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """指定期間の取引履歴を取得するヘルパー関数"""
        conn = None
        try:
            conn = get_db_connection()
            query = """
            SELECT t.code, s.name, t.trade_type, t.quantity, t.price, t.trade_date
            FROM transactions t
            JOIN stocks s ON t.code = s.code
            WHERE t.trade_date BETWEEN %s AND %s
            ORDER BY t.trade_date ASC
            """
            df = pd.read_sql_query(query, conn, params=(start_date, end_date))
            logger.info(
                f"DB取引履歴取得: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')} ({len(df)}件)"
            )
            return df
        except PgError as e:
            logger.error(f"DB取引履歴取得エラー: {e}")
            return pd.DataFrame()
        finally:
            if conn:
                conn.close()

    def get_portfolio_pnl(self, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """
        指定期間のポートフォリオ全体の損益を計算する
        Args:
            start_date: 計算開始日
            end_date: 計算終了日
        Returns:
            Dict[str, float]: 総損益、実現損益、評価損益
        """
        holdings_df = self.get_portfolio()
        if holdings_df.empty:
            return {"total_pnl": 0.0, "realized_pnl": 0.0, "unrealized_pnl": 0.0}

        transactions_df = self._get_transactions(start_date, end_date)

        realized_pnl = 0.0
        # 実現損益の計算 (期間内の売却取引から計算)
        sell_transactions = transactions_df[transactions_df["trade_type"] == "sell"]
        for _, row in sell_transactions.iterrows():
            # 簡略化のため、ここでは売却価格 - 購入価格の単純計算とする
            # 実際にはFIFO/LIFOなどの会計処理が必要
            realized_pnl += row["quantity"] * (
                row["price"] - row["purchase_price"]
            )  # purchase_priceはtransactionsテーブルにないため、仮のロジック

        unrealized_pnl = 0.0
        # 評価損益の計算 (期間終了時点の保有銘柄の評価額 - 購入額)
        for _, holding in holdings_df.iterrows():
            ticker = holding["code"]
            latest_price_df = self.fetch_stock_data(ticker, period="1d")
            if not latest_price_df.empty:
                latest_price = latest_price_df["Close"].iloc[-1]
                unrealized_pnl += holding["quantity"] * (latest_price - holding["purchase_price"])

        total_pnl = realized_pnl + unrealized_pnl
        return {
            "total_pnl": total_pnl,
            "realized_pnl": realized_pnl,
            "unrealized_pnl": unrealized_pnl,
        }

    def get_portfolio_asset_allocation(self) -> Dict[str, Dict[str, float]]:
        """
        現在のポートフォリオの資産配分（セクター別、銘柄別）を計算する
        Returns:
            Dict[str, Dict[str, float]]: セクター別配分、銘柄別配分
        """
        holdings_df = self.get_portfolio()
        if holdings_df.empty:
            return {"sector_allocation": {}, "stock_allocation": {}}

        total_market_value = 0.0
        stock_market_values = {}
        sector_market_values = {}

        for _, holding in holdings_df.iterrows():
            ticker = holding["code"]
            latest_price_df = self.fetch_stock_data(ticker, period="1d")
            if not latest_price_df.empty:
                latest_price = latest_price_df["Close"].iloc[-1]
                market_value = holding["quantity"] * latest_price
                total_market_value += market_value
                stock_market_values[holding["name"]] = market_value

                purpose = holding["purpose"] # sectorをpurposeに置き換え
                sector_market_values[purpose] = sector_market_values.get(purpose, 0.0) + market_value # sectorをpurposeに置き換え

        sector_allocation = (
            {purpose: (value / total_market_value) * 100 for purpose, value in sector_market_values.items()} # sectorをpurposeに置き換え
            if total_market_value > 0
            else {}
        )
        stock_allocation = (
            {stock: (value / total_market_value) * 100 for stock, value in stock_market_values.items()}
            if total_market_value > 0
            else {}
        )

        return {"sector_allocation": sector_allocation, "stock_allocation": stock_allocation}

    def get_portfolio_monthly_performance(self, end_date: datetime) -> Dict[str, float]:
        """
        月間のポートフォリオパフォーマンスを計算する
        Args:
            end_date: 計算終了日 (通常は月末)
        Returns:
            Dict[str, float]: 総投資額、総リターン、年率リターン、シャープレシオ、月間損益、月間資産配分変化
        """
        # TODO: 実際の投資額、リターン、シャープレシオの計算ロジックを実装
        # 現状はダミーデータまたは簡略化された計算
        start_date = end_date.replace(day=1)  # 月初
        monthly_pnl = self.get_portfolio_pnl(start_date, end_date)["total_pnl"]

        # ダミーデータ
        total_investment = 1000000.0
        total_return = 50000.0
        annualized_return = 0.06
        sharpe_ratio = 1.2

        # 資産配分の変化は、前月との比較が必要。ここでは簡略化
        asset_allocation_change = 0.01  # 例: 1%の変化

        return {
            "total_investment": total_investment,
            "total_return": total_return,
            "annualized_return": annualized_return,
            "sharpe_ratio": sharpe_ratio,
            "monthly_pnl": monthly_pnl,
            "asset_allocation_change": asset_allocation_change,
        }

    def get_portfolio_rebalancing_suggestions(self) -> str:
        """
        ポートフォリオの再構築検討事項を提案する
        Returns:
            str: 再構築に関する提案テキスト
        """
        allocation = self.get_portfolio_asset_allocation()
        suggestions = []

        # 例: 特定セクターへの偏りがあれば警告
        for sector, percentage in allocation["sector_allocation"].items():
            if percentage > 30:  # 例: 30%以上は偏り
                suggestions.append(
                    f"・{sector} セクターへの集中度が高い ({percentage:.2f}%) です。分散を検討してください。"
                )

        # 例: パフォーマンスの悪い銘柄があれば検討を促す
        # TODO: 銘柄ごとのパフォーマンスデータを取得し、評価するロジックを追加
        suggestions.append("・パフォーマンスが継続的に低い銘柄の見直しを検討してください。")
        suggestions.append(
            "・市場環境の変化に応じて、成長が見込まれるセクターへの投資比率を高めることを検討してください。"
        )

        if not suggestions:
            return "現在のポートフォリオはバランスが取れています。大きな再構築の必要はありません。"
        return "\n".join(suggestions)

    def get_individual_stock_performance(self, code: str, start_date: datetime, end_date: datetime) -> Dict:
        """
        個別銘柄の指定期間での損益、売買履歴、今後の見通しを計算する
        Args:
            code: 銘柄コード
            start_date: 計算開始日
            end_date: 計算終了日
        Returns:
            Dict: 銘柄のパフォーマンス情報
        """
        conn = None
        try:
            conn = get_db_connection()
            # 銘柄名と目的を取得
            stock_info_query = "SELECT name, purpose FROM stocks WHERE code = %s" # sectorをpurposeに置き換え
            with conn.cursor() as cursor:
                cursor.execute(stock_info_query, (code,))
                stock_info = cursor.fetchone()
            if not stock_info:
                return {"error": f"銘柄コード {code} が見つかりません。"}
            stock_name, stock_purpose = stock_info # stock_sectorをstock_purposeに置き換え

            # 売買履歴
            transactions_query = """
            SELECT trade_type, quantity, price, trade_date
            FROM transactions
            WHERE code = %s AND trade_date BETWEEN %s AND %s
            ORDER BY trade_date ASC
            """
            transactions_df = pd.read_sql_query(transactions_query, conn, params=(code, start_date, end_date))

            # 期間内の損益計算 (簡略化)
            pnl = 0.0
            for _, row in transactions_df.iterrows():
                if row["trade_type"] == "sell":
                    # 簡略化: 売却価格から購入価格を引く (購入価格は別途取得が必要)
                    # ここでは、購入価格が不明なため、単純に売却額を計上
                    pnl += row["quantity"] * row["price"]
                elif row["trade_type"] == "buy":
                    pnl -= row["quantity"] * row["price"]

            # 最新株価の取得
            latest_price_df = self.fetch_stock_data(code, period="1d")
            latest_price = latest_price_df["Close"].iloc[-1] if not latest_price_df.empty else None

            # 今後の見通し (ダミー)
            outlook = "市場全体の動向と目的の成長性に基づき、中立的な見通しです。" # セクターを目的の成長性に置き換え

            return {
                "code": code,
                "name": stock_name,
                "purpose": stock_purpose, # sectorをpurposeに置き換え
                "pnl": pnl,
                "transactions": transactions_df.to_dict(orient="records"),
                "latest_price": latest_price,
                "outlook": outlook,
            }
        except PgError as e:
            logger.error(f"個別銘柄パフォーマンス取得エラー: {e}")
            return {"error": str(e)}
        finally:
            if conn:
                conn.close()


if __name__ == "__main__":
    analyzer = PortfolioAnalyzer()
    analyzer.analyze_portfolio()

    # テスト実行
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    last_week = today - timedelta(weeks=1)
    last_month = today - timedelta(days=30)  # 簡易的な月初

    print("\n--- 日次損益テスト ---")
    daily_pnl = analyzer.get_portfolio_pnl(yesterday, today)
    print(f"日次損益: {daily_pnl}")

    print("\n--- 週次損益テスト ---")
    weekly_pnl = analyzer.get_portfolio_pnl(last_week, today)
    print(f"週次損益: {weekly_pnl}")

    print("\n--- 資産配分テスト ---")
    asset_allocation = analyzer.get_portfolio_asset_allocation()
    print(f"資産配分: {asset_allocation}")

    print("\n--- 月次パフォーマンステスト ---")
    monthly_performance = analyzer.get_portfolio_monthly_performance(today)
    print(f"月次パフォーマンス: {monthly_performance}")

    print("\n--- 再構築検討事項テスト ---")
    rebalancing_suggestions = analyzer.get_portfolio_rebalancing_suggestions()
    print(f"再構築検討事項:\n{rebalancing_suggestions}")

    print("\n--- 個別銘柄月間パフォーマンステスト (例: 7203) ---")
    # ダミーの銘柄コードを使用
    individual_performance = analyzer.get_individual_stock_performance("7203", last_month, today)
    print(f"個別銘柄パフォーマンス:\n{individual_performance}")
