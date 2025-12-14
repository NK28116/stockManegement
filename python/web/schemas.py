from typing import Optional

from pydantic import BaseModel


class TradingRules(BaseModel):
    stop_loss_percent: float
    take_profit_percent: float
    trailing_stop_percent: float
    risk_per_trade: float
    max_loss_percent: float
    crash_threshold: float
    volatility_threshold: float
    volume_spike_threshold: float
    rsi_overbought_threshold: float
    rsi_oversold_threshold: float
    macd_fast_period: int
    macd_slow_period: int
    macd_signal_period: int
    bollinger_period: int
    bollinger_std: int


class TradingRulesUpdate(BaseModel):
    stop_loss_percent: Optional[float] = None
    take_profit_percent: Optional[float] = None
    trailing_stop_percent: Optional[float] = None
    risk_per_trade: Optional[float] = None
    max_loss_percent: Optional[float] = None
    crash_threshold: Optional[float] = None
    volatility_threshold: Optional[float] = None
    volume_spike_threshold: Optional[float] = None
    rsi_overbought_threshold: Optional[float] = None
    rsi_oversold_threshold: Optional[float] = None
    macd_fast_period: Optional[int] = None
    macd_slow_period: Optional[int] = None
    macd_signal_period: Optional[int] = None
    bollinger_period: Optional[int] = None
    bollinger_std: Optional[int] = None
