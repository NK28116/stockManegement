"""Technical indicator settings.

All numerical thresholds for RSI, MACD, ATR, EMA, Bollinger Bands, and volume.
Used by pattern detection (swing_trade_rules.py) and risk calculation (risk_management.py).
"""

# --- Trend (EMA) ---
EMA_SHORT_PERIOD = 20
EMA_LONG_PERIOD = 50

# --- RSI ---
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
RSI_ENTRY_LOWER = 50
RSI_ENTRY_UPPER = 60
RSI_TRIANGLE_MIN = 55
RSI_LONG_RANGE = (40, 65)
RSI_SHORT_RANGE = (35, 60)

# --- MACD ---
MACD_FAST_PERIOD = 12
MACD_SLOW_PERIOD = 26
MACD_SIGNAL_PERIOD = 9

# --- ATR ---
ATR_PERIOD = 14
ATR_BASELINE_PERIOD = 20

# --- Bollinger Bands ---
BOLLINGER_PERIOD = 20
BOLLINGER_STD = 2.0

# --- Volume ---
VOLUME_MA_PERIOD = 5
VOLUME_BREAKOUT_MULTIPLIER = 1.2
VOLUME_MA_PERIOD_LONG = 20

# --- Market filters (legacy, kept for config.py compatibility) ---
CRASH_THRESHOLD_PCT = -3.0
VOLATILITY_THRESHOLD_PCT = 3.0
VOLUME_SPIKE_THRESHOLD = 2.0
