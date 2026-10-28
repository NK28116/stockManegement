from datetime import datetime

from python.trading.rules import indicator_settings
from python.trading.rules import risk_management as risk_rules
from python.utils.gcs_client import gcs
from python.web.schemas import (
    BollingerIndicator,
    EntryRules,
    ExitRules,
    ExitToggleRule,
    Indicators,
    MACDFilterRule,
    MACDIndicator,
    MarketFilters,
    PriceMomentumRule,
    RiskManagementRules,
    RSIFilterRule,
    RSIIndicator,
    RuleMeta,
    TradingRules,
)

# Active rules path relative to bucket root or data/ dir
ACTIVE_RULES_PATH = "trading_rules/active.json"


def get_active_rules() -> TradingRules:
    """
    アクティブな取引ルールを取得する。
    GCSまたはローカルから読み込み、失敗した場合はデフォルトルールを返す。
    """
    data = gcs.get_json(ACTIVE_RULES_PATH)
    if data:
        try:
            # Ensure it validates against the schema
            return TradingRules.model_validate(data)
        except Exception as e:
            print(
                f"[WARNING] Failed to validate active rules from {ACTIVE_RULES_PATH}: {e}. using defaults."
            )

    return get_default_rules()


def get_default_rules() -> TradingRules:
    """
    デフォルトの取引ルールを生成する。
    数値は python/trading/rules/ 配下の定数ファイルから取得する。
    """
    return TradingRules(
        meta=RuleMeta(
            version=0,
            description="Default Rules (Fallback)",
            updated_at=datetime.utcnow(),
            updated_by="system",
            active=True,
        ),
        risk_management=RiskManagementRules(
            stop_loss_percent=risk_rules.STOP_LOSS_PERCENT_LEGACY,
            take_profit_percent=risk_rules.TAKE_PROFIT_PERCENT_LEGACY,
            trailing_stop_percent=risk_rules.TRAILING_STOP_PERCENT,
            risk_per_trade=risk_rules.RISK_PER_TRADE,
            max_daily_loss_percent=risk_rules.MAX_DAILY_LOSS_PCT,
        ),
        entry_rules=EntryRules(
            price_momentum=PriceMomentumRule(enabled=True, pattern="++"),
            rsi_filter=RSIFilterRule(
                enabled=True, oversold=indicator_settings.RSI_OVERSOLD
            ),
            macd_filter=MACDFilterRule(enabled=True, require_cross=True),
        ),
        exit_rules=ExitRules(
            stop_loss=ExitToggleRule(enabled=True),
            take_profit=ExitToggleRule(enabled=True),
            dead_cross_exit=ExitToggleRule(enabled=True, pattern="--"),
        ),
        indicators=Indicators(
            rsi=RSIIndicator(
                period=indicator_settings.RSI_PERIOD,
                overbought=indicator_settings.RSI_OVERBOUGHT,
                oversold=indicator_settings.RSI_OVERSOLD,
            ),
            macd=MACDIndicator(
                fast_period=indicator_settings.MACD_FAST_PERIOD,
                slow_period=indicator_settings.MACD_SLOW_PERIOD,
                signal_period=indicator_settings.MACD_SIGNAL_PERIOD,
            ),
            bollinger=BollingerIndicator(
                period=indicator_settings.BOLLINGER_PERIOD,
                std=indicator_settings.BOLLINGER_STD,
            ),
        ),
        filters=MarketFilters(
            crash_threshold_percent=indicator_settings.CRASH_THRESHOLD_PCT,
            volatility_threshold=indicator_settings.VOLATILITY_THRESHOLD_PCT,
            volume_spike_threshold=indicator_settings.VOLUME_SPIKE_THRESHOLD,
        ),
    )
