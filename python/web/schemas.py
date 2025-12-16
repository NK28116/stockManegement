from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator, Field

# ---------------------------
# Meta
# ---------------------------


class RuleMeta(BaseModel):
    version: int
    description: str
    updated_at: datetime
    updated_by: str
    comment: Optional[str] = None
    active: bool = True


# ---------------------------
# Risk Management
# ---------------------------


class RiskManagementRules(BaseModel):
    stop_loss_percent: float
    take_profit_percent: float
    trailing_stop_percent: float
    risk_per_trade: float
    max_daily_loss_percent: float

    @field_validator("*")
    @classmethod
    def check_percent(cls, v: float, info):
        # Allow 0 for disabled/unused, otherwise expects 0 < x < 1 typically,
        # but original code enforced 0 < value < 1 strictly.
        if isinstance(v, (int, float)):
            if not (0 < v < 1):
                # Some legacy values might be exactly 0 or 1, but original code raised ValueError
                raise ValueError(f"{info.field_name} must be between 0 and 1, got {v}")
        return v


# ---------------------------
# Entry Rules
# ---------------------------


class PriceMomentumRule(BaseModel):
    enabled: bool
    pattern: str  # "++"


class RSIFilterRule(BaseModel):
    enabled: bool
    oversold: int


class MACDFilterRule(BaseModel):
    enabled: bool
    require_cross: bool


class EntryRules(BaseModel):
    price_momentum: PriceMomentumRule
    rsi_filter: RSIFilterRule
    macd_filter: MACDFilterRule


# ---------------------------
# Exit Rules
# ---------------------------


class ExitToggleRule(BaseModel):
    enabled: bool
    pattern: Optional[str] = None


class ExitRules(BaseModel):
    stop_loss: ExitToggleRule
    take_profit: ExitToggleRule
    dead_cross_exit: ExitToggleRule


# ---------------------------
# Indicators
# ---------------------------


class RSIIndicator(BaseModel):
    period: int
    overbought: int
    oversold: int


class MACDIndicator(BaseModel):
    fast_period: int
    slow_period: int
    signal_period: int


class BollingerIndicator(BaseModel):
    period: int
    std: float


class Indicators(BaseModel):
    rsi: RSIIndicator
    macd: MACDIndicator
    bollinger: BollingerIndicator


# ---------------------------
# Filters
# ---------------------------


class MarketFilters(BaseModel):
    crash_threshold_percent: float
    volatility_threshold: float
    volume_spike_threshold: float


# ---------------------------
# Change Reason
# ---------------------------
class ChangeReason(str, Enum):
    PERFORMANCE = "Performance Optimization"
    RISK = "Risk Mitigation"
    MARKET = "Market Regime Change"
    FIX = "Logic Correction"
    REGULAR = "Regular Update"
    TEST = "Testing"
    OTHER = "Other"


# ---------------------------
# Root TradingRules
# ---------------------------


class TradingRules(BaseModel):
    meta: RuleMeta
    risk_management: RiskManagementRules
    entry_rules: EntryRules
    exit_rules: ExitRules
    indicators: Indicators
    filters: MarketFilters
    change_reason: ChangeReason = Field(
        default=ChangeReason.REGULAR,
        description="Reason for this rule change"
    )
    change_note: Optional[str] = Field(
        default="",
        description="Optional detailed note about the change"
    )

    @property
    def is_active(self) -> bool:
        return self.meta.active
