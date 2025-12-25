"""
Analytics API Router

ポートフォリオ分析APIのエンドポイント定義
総資産額と評価損益のサマリーを提供
"""
from fastapi import APIRouter, HTTPException, Query

from python.utils.logger import get_logger
from python.web.schemas import AnalyticsSummaryResponse
from python.web.services.analytics import analytics_service

logger = get_logger("analytics_router", category="web")

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary(
    portfolio_name: str = Query(
        default="my_stock", description="分析対象のポートフォリオ名"
    )
) -> AnalyticsSummaryResponse:
    """
    ポートフォリオ分析サマリーを取得

    総資産額（現在の評価額合計）と評価損益を計算して返却

    Args:
        portfolio_name: 分析対象のポートフォリオ名（デフォルト: "my_stock"）

    Returns:
        AnalyticsSummaryResponse: 分析結果
            - portfolio_name: ポートフォリオ名
            - total_assets: 総資産額
            - total_investment: 総投資額
            - unrealized_pnl: 評価損益
            - unrealized_pnl_percent: 評価損益率（パーセント）
            - last_updated: 最終更新日時
    """
    try:
        logger.info(f"GET /api/analytics/summary: portfolio_name={portfolio_name}")
        result = analytics_service.calculate_total_performance(portfolio_name)
        logger.info(f"分析結果: {result.model_dump()}")
        return result
    except Exception as e:
        logger.error(f"分析エラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"分析処理でエラーが発生しました: {e}")
