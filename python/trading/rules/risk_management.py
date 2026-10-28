"""Risk management and signal scoring configuration.

Stop loss / take profit methods, risk-per-trade limits, and the scoring
system used to decide whether a setup qualifies as an entry signal.
"""

# --- Stop loss ---
STOP_LOSS_METHOD = "swing_or_atr"
ATR_STOP_MULTIPLIER = 1.2

# --- Take profit ---
RISK_REWARD_RATIO_MIN = 1.5
ATR_TP_MULTIPLIER = ATR_STOP_MULTIPLIER * RISK_REWARD_RATIO_MIN  # 1.8
TAKE_PROFIT_METHODS = (
    "risk_reward_15x",
    "prior_swing_high",
    "fib_1272",
    "fib_1618",
)

# --- Percent-based limits ---
STOP_LOSS_PERCENT_LEGACY = 0.05
TAKE_PROFIT_PERCENT_LEGACY = 0.10
TRAILING_STOP_PERCENT = 0.03
RISK_PER_TRADE = 0.01
MAX_DAILY_LOSS_PCT = 0.03

# --- Scoring (7-point scale) ---
SCORE_WEIGHTS = {
    "pattern_match": 2,
    "volume_match": 1,
    "rsi_match": 1,
    "macd_match": 1,
    "trend_match": 2,
}
SCORE_MAX = sum(SCORE_WEIGHTS.values())  # 7
SCORE_THRESHOLD_ENTRY = 5
SCORE_THRESHOLD_WATCH = 4

# --- Weakness detection (for long exit) ---
RSI_WEAKNESS_THRESHOLD = 70
UPPER_SHADOW_CONSECUTIVE = 2
