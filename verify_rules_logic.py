import os
import sys
import pandas as pd
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from python.trading.trading_rules import ImprovedTradingRules
from python.web.schemas import (
    TradingRules,
    RuleMeta,
    RiskManagementRules,
    EntryRules,
    ExitRules,
    Indicators,
    MarketFilters,
    PriceMomentumRule,
    RSIFilterRule,
    MACDFilterRule,
    ExitToggleRule,
    RSIIndicator,
    MACDIndicator,
    BollingerIndicator,
)


def test_dynamic_rules():
    print("=== Testing Dynamic Rules Injection ===")

    # 1. Test Dynamic Configuration
    print("\n1. Testing Dynamic Config (Injection)")
    custom_stop_loss = 0.99  # 99% stop loss (extreme value for testing)

    # Create a custom TradingRules object with nested structure
    custom_rules_schema = TradingRules(
        meta=RuleMeta(
            version="1.0",
            description="Test Rules",
            updated_at=datetime.now(),
            updated_by="Test",
            active=True,
        ),
        risk_management=RiskManagementRules(
            stop_loss_percent=custom_stop_loss,
            take_profit_percent=0.10,
            trailing_stop_percent=0.03,
            risk_per_trade=0.02,  # Fixed: ensure 0 < value < 1
            max_daily_loss_percent=0.03,
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

    rules_custom = ImprovedTradingRules(rules=custom_rules_schema)
    print(f"  Custom Stop Loss: {rules_custom.rules.risk_management.stop_loss_percent}")
    assert (
        rules_custom.rules.risk_management.stop_loss_percent == custom_stop_loss
    ), "Instance should use injected value"

    # 2. Test Logic Impact
    print("\n2. Testing Logic Impact")
    # Create dummy DataFrame
    df = pd.DataFrame(
        {"Close": [100, 105, 110, 100, 90, 80], "Volume": [1000] * 6}, index=pd.date_range("2024-01-01", periods=6)
    )

    # Analyze with custom rules
    trades = rules_custom.analyze_with_improved_rules(df)

    # Just verify that it runs and returns a list (logic verification is more complex, but this proves integration)
    assert isinstance(trades, list)
    print(f"  Analysis returned {len(trades)} trades/actions")

    print("\n✅ Verification Successful!")


if __name__ == "__main__":
    try:
        test_dynamic_rules()
    except AssertionError as e:
        print(f"\n❌ Verification Failed: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
