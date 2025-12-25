"""
Analytics Service

ポートフォリオの分析機能を提供するサービス層
総資産額と評価損益を計算
"""
from datetime import datetime
from typing import Dict

from python.analysis.portfolio_analyzer import PortfolioAnalyzer
from python.utils.logger import get_logger
from python.web.schemas import AnalyticsSummaryResponse

logger = get_logger("analytics_service", category="web")


class AnalyticsService:
    """
    分析サービスクラス
    PortfolioAnalyzerを利用してポートフォリオの総資産額と評価損益を計算
    """

    def __init__(self):
        self.analyzer = PortfolioAnalyzer(is_test_mode=False)

    def calculate_total_performance(
        self, portfolio_name: str = "my_stock"
    ) -> AnalyticsSummaryResponse:
        """
        ポートフォリオの総資産額と評価損益を計算

        Args:
            portfolio_name: ポートフォリオ名（デフォルト: "my_stock"）

        Returns:
            AnalyticsSummaryResponse: 分析結果（総資産額、評価損益など）
        """
        logger.info(f"分析開始: portfolio_name={portfolio_name}")

        # ポートフォリオデータ取得
        portfolio_df = self.analyzer.get_portfolio(portfolio_name)

        if portfolio_df.empty:
            logger.warning(f"ポートフォリオが見つかりません: {portfolio_name}")
            return AnalyticsSummaryResponse(
                portfolio_name=portfolio_name,
                total_assets=0.0,
                total_investment=0.0,
                unrealized_pnl=0.0,
                unrealized_pnl_percent=0.0,
                last_updated=datetime.now(),
            )

        # 総投資額の計算
        total_investment = (
            portfolio_df["quantity"] * portfolio_df["purchase_price"]
        ).sum()

        # 総資産額（現在評価額）の計算
        total_assets = 0.0
        for _, holding in portfolio_df.iterrows():
            ticker = holding["code"]
            quantity = holding["quantity"]

            # 最新株価を取得（1日分のデータで十分）
            latest_price_df = self.analyzer.fetch_stock_data(ticker, period="1d")

            if not latest_price_df.empty:
                latest_price = latest_price_df["Close"].iloc[-1]
                total_assets += quantity * latest_price
                logger.debug(
                    f"{ticker}: quantity={quantity}, latest_price={latest_price}, value={quantity * latest_price}"
                )
            else:
                logger.warning(f"株価データ取得失敗: {ticker}、購入価格で代替")
                # 株価取得失敗時は購入価格で代替
                total_assets += quantity * holding["purchase_price"]

        # 評価損益の計算
        unrealized_pnl = total_assets - total_investment

        # 評価損益率の計算（パーセント）
        unrealized_pnl_percent = (
            (unrealized_pnl / total_investment * 100) if total_investment > 0 else 0.0
        )

        logger.info(
            f"分析完了: total_assets={total_assets:.2f}, total_investment={total_investment:.2f}, "
            f"unrealized_pnl={unrealized_pnl:.2f}, unrealized_pnl_percent={unrealized_pnl_percent:.2f}%"
        )

        return AnalyticsSummaryResponse(
            portfolio_name=portfolio_name,
            total_assets=total_assets,
            total_investment=total_investment,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_percent=unrealized_pnl_percent,
            last_updated=datetime.now(),
        )


# サービスインスタンス（シングルトンとして利用）
analytics_service = AnalyticsService()
