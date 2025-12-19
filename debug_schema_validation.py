from datetime import datetime
from python.web.schemas import (
    TradingRules,
    RuleMeta,
    RiskManagementRules,
    EntryRules,
    PriceMomentumRule,
    RSIFilterRule,
    MACDFilterRule,
    ExitRules,
    ExitToggleRule,
    Indicators,
    RSIIndicator,
    MACDIndicator,
    BollingerIndicator,
    MarketFilters,
    ChangeReason,
)
import json


def test_validation():
    print("--- Testing Pydantic Validation ---")

    # Base valid data (mimicking rules_loader defaults)
    base_data = {
        "meta": {
            "version": 1,
            "description": "Test",
            "updated_at": datetime.utcnow().isoformat(),
            "updated_by": "tester",
            "active": True,
        },
        "risk_management": {
            "stop_loss_percent": 0.05,
            "take_profit_percent": 0.10,
            "trailing_stop_percent": 0.03,
            "risk_per_trade": 0.02,
            "max_daily_loss_percent": 0.03,
        },
        "entry_rules": {
            "price_momentum": {"enabled": True, "pattern": "++"},
            "rsi_filter": {"enabled": True, "oversold": 30},
            "macd_filter": {"enabled": True, "require_cross": True},
        },
        "exit_rules": {
            "stop_loss": {"enabled": True},
            "take_profit": {"enabled": True},
            "dead_cross_exit": {"enabled": True, "pattern": "--"},
        },
        "indicators": {
            "rsi": {"period": 14, "overbought": 70, "oversold": 30},
            "macd": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
            "bollinger": {"period": 20, "std": 2.0},
        },
        "filters": {"crash_threshold_percent": -3.0, "volatility_threshold": 3.0, "volume_spike_threshold": 2.0},
        "change_reason": "Regular Update",
        "change_note": "Test note",
    }

    # Test 1: Valid Data
    try:
        TradingRules.model_validate(base_data)
        print("[PASS] Base data validated.")
    except Exception as e:
        print(f"[FAIL] Base data failed: {e}")

    # Test 2: Zero Percent in Risk Management
    data_zero = base_data.copy()
    data_zero["risk_management"] = base_data["risk_management"].copy()
    data_zero["risk_management"]["stop_loss_percent"] = 0.0
    try:
        TradingRules.model_validate(data_zero)
        print("[FAIL] Zero percent should probably be allowed but Validator might fail it.")
    except Exception as e:
        print(f"[EXPECTED FAIL] Zero percent validation: {e}")

    # Test 3: Invalid Change Reason
    data_enum = base_data.copy()
    data_enum["change_reason"] = "Invalid Reason"
    try:
        TradingRules.model_validate(data_enum)
        print("[FAIL] Invalid enum should fail.")
    except Exception as e:
        print(f"[EXPECTED FAIL] Enum validation: {e}")

    # Test 4: Missing field (e.g. change_note which is Optional but maybe frontend sends null?)
    data_missing = base_data.copy()
    data_missing["change_note"] = None  # Should be allowed as Optional[str]
    try:
        TradingRules.model_validate(data_missing)
        print("[PASS] None for Optional field validated.")
    except Exception as e:
        print(f"[FAIL] None for Optional field failed: {e}")

    # Test 5: Float in Integer field (RSI period)
    data_type = base_data.copy()
    data_type["indicators"]["rsi"]["period"] = 14.5
    try:
        TradingRules.model_validate(data_type)
        print("[FAIL] Float for Int should fail (or coerce if pydantic allows).")
    except Exception as e:
        print(f"[INFO] Type check: {e}")


if __name__ == "__main__":
    test_validation()
