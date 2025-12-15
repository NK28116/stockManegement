import json
from datetime import datetime
from pathlib import Path

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

# Active rules path
RULES_DIR = Path("data/rules")
ACTIVE_RULES_PATH = RULES_DIR / "trading_rules.active.json"


def get_active_rules() -> TradingRules:
    """
    アクティブな取引ルールを取得する。
    ファイルが存在しない、または読み込みに失敗した場合はデフォルトルールを返す。
    """
    if ACTIVE_RULES_PATH.exists():
        try:
            with open(ACTIVE_RULES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Ensure it validates against the schema
            return TradingRules.model_validate(data)
        except Exception as e:
            # logging could be added here
            print(
                f"[WARNING] Failed to load active rules from {ACTIVE_RULES_PATH}: {e}. using defaults."
            )

    return get_default_rules()


def get_default_rules() -> TradingRules:
    """
    デフォルトの取引ルールを生成する。
    config.py の値をベースにしたハードコードされたデフォルト値。
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
            stop_loss_percent=0.05,  # 5%
            take_profit_percent=0.10,  # 10%
            trailing_stop_percent=0.03,  # 3%
            risk_per_trade=0.02,  # 2%
            max_daily_loss_percent=0.03,  # 3%
        ),
        entry_rules=EntryRules(
            price_momentum=PriceMomentumRule(enabled=True, pattern="++"),
            rsi_filter=RSIFilterRule(enabled=True, oversold=30),
            macd_filter=MACDFilterRule(enabled=True, require_cross=True),
        ),
        exit_rules=ExitRules(
            stop_loss=ExitToggleRule(enabled=True),
            take_profit=ExitToggleRule(enabled=True),
            dead_cross_exit=ExitToggleRule(enabled=True, pattern="--"),
        ),
        indicators=Indicators(
            rsi=RSIIndicator(
                period=14,
                overbought=70,
                oversold=30,
            ),
            macd=MACDIndicator(
                fast_period=12,
                slow_period=26,
                signal_period=9,
            ),
            bollinger=BollingerIndicator(
                period=20,
                std=2.0,
            ),
        ),
        filters=MarketFilters(
            crash_threshold_percent=-3.0,
            volatility_threshold=3.0,
            volume_spike_threshold=2.0,
        ),
    )
