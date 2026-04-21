"""Swing trade rule constants.

Three logical groups:
    - swing_trade_rules: chart pattern definitions (double bottom, H&S, flag, triangle)
    - indicator_settings: numerical thresholds for RSI, MACD, ATR, EMA, Bollinger, volume
    - risk_management: stop loss, take profit, risk/reward, scoring weights

Reference: README.md ("トレード戦略仕様" section)
"""

from python.trading.rules import (
    indicator_settings,
    risk_management,
    swing_trade_rules,
)

__all__ = ["indicator_settings", "risk_management", "swing_trade_rules"]
