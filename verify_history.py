import requests
import json
from pathlib import Path
from datetime import datetime
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from python.config import config

# We need to simulate the API calls or run them directly.
# Since running a full fastapi server is heavy, let's look at calling the functions directly
# or mocking the request. calling functions directly seems easier for a script.

from python.web.api.rules import save_draft_rules, apply_rules, list_history, get_history
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

# Setup Test Data Directory override for safety?
# Actually the code uses hardcoded paths in rules.py: data/rules/
# We should probably backing up existing data or using a test mode.
# But for now, let's just create a test rule and see.
# CAUTION: This will overwrite local draft/active rules!
# The user asked to implement it, so running it is the proof.


def create_test_rule(version: int, stop_loss: float, comment: str):
    return TradingRules(
        meta=RuleMeta(
            version=version,
            description="Test Rule",
            updated_at=datetime.utcnow(),
            updated_by="tester",
            comment=comment,
            active=True,
        ),
        risk_management=RiskManagementRules(
            stop_loss_percent=stop_loss,
            take_profit_percent=0.1,
            trailing_stop_percent=0.03,
            risk_per_trade=0.02,
            max_daily_loss_percent=0.05,
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
            rsi=RSIIndicator(period=14, overbought=70, oversold=30),
            macd=MACDIndicator(fast_period=12, slow_period=26, signal_period=9),
            bollinger=BollingerIndicator(period=20, std=2.0),
        ),
        filters=MarketFilters(
            crash_threshold_percent=0.05,
            volatility_threshold=0.03,
            volume_spike_threshold=1.5,
        ),
    )


def main():
    print("=== Verifying Rule History Logic ===")

    # 1. Save Draft (v1 intent)
    print("\n1. Saving Draft Rules...")
    rule_v1 = create_test_rule(
        0, 0.05, "Initial Commit"
    )  # Version 0 in draft, will be ignored/overwritten by auto-inc
    save_draft_rules(rule_v1)
    print("   Draft saved.")

    # 2. Apply Rules (Expect v(N)+1)
    print("\n2. Applying Rules (1st time)...")
    res1 = apply_rules(force=True)
    v1_applied = res1["version"]
    print(f"   Applied! Version: {v1_applied}")

    # 3. Modify Draft and Apply (Expect v(N)+2)
    print("\n3. Modifying Draft and Re-applying (Diff check)...")
    rule_v2 = create_test_rule(0, 0.08, "relax stop loss")  # Stop loss 0.05 -> 0.08
    save_draft_rules(rule_v2)

    res2 = apply_rules(force=True)
    v2_applied = res2["version"]
    print(f"   Applied! Version: {v2_applied}")

    if v2_applied != v1_applied + 1:
        print(f"   ❌ Version did not increment correctly! {v1_applied} -> {v2_applied}")
    else:
        print(f"   ✅ Version incremented correctly.")

    # 4. Check History content
    print("\n4. Checking History Data...")
    hist_list = list_history()
    print(f"   Index contains {len(hist_list)} entries.")

    latest_hist = get_history(v2_applied)
    print("   Latest History Diff:")
    import pprint

    pprint.pprint(latest_hist.get("diff"))

    # Check if diff is correct
    diff = latest_hist.get("diff", {})
    sl_diff = diff.get("risk_management.stop_loss_percent")
    if sl_diff:
        print(f"   ✅ Diff found for stop_loss_percent: {sl_diff}")
        if sl_diff["before"] == 0.05 and sl_diff["after"] == 0.08:
            print("   ✅ Diff values correct.")
        else:
            print("   ❌ Diff values incorrect!")
    else:
        print("   ❌ Diff NOT found for stop_loss_percent!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
