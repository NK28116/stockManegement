"""Chart pattern definitions for swing trading.

Each pattern is a dict of condition parameters. Pattern detection code
(python/watch/analyze.py etc.) reads these to determine whether a pattern
is present.

Time frame: daily (auxiliary: 4h).
Holding period: 3-10 business days, max 2 weeks.
"""

# --- Time frame / holding period ---
TIMEFRAME_MAIN = "1d"
TIMEFRAME_AUX = "4h"
HOLD_DAYS_MIN = 3
HOLD_DAYS_MAX = 10
HOLD_DAYS_HARD_LIMIT = 14

# --- Long patterns ---

DOUBLE_BOTTOM = {
    "min_days": 5,
    "max_days": 12,
    "price_tolerance_pct": 0.03,
    "rsi_start": 50,
    "rsi_target": 60,
    "require_neckline_break": True,
}

INVERSE_HEAD_SHOULDERS = {
    "min_days": 7,
    "max_days": 15,
    "right_shoulder_higher_than_left": True,
    "require_neckline_break": True,
    "require_macd_golden_cross": True,
}

ASCENDING_FLAG = {
    "prior_uptrend_min_pct": 0.05,
    "prior_uptrend_max_pct": 0.10,
    "consolidation_days_min": 3,
    "consolidation_days_max": 7,
    "require_volume_decline_in_consolidation": True,
}

ASCENDING_TRIANGLE = {
    "min_days": 5,
    "max_days": 15,
    "require_flat_resistance": True,
    "require_rising_support": True,
    "rsi_min": 55,
}

DOWNTREND_LINE_BREAK_RETEST = {
    "require_breakout": True,
    "require_successful_retest": True,
}

# --- Short patterns ---

DOUBLE_TOP = {
    "price_tolerance_pct": 0.03,
    "rsi_start": 70,
    "require_neckline_break": True,
}

HEAD_AND_SHOULDERS = {
    "right_shoulder_weaker": True,
    "require_neckline_break": True,
    "require_macd_dead_cross": True,
}

DESCENDING_FLAG = {
    "consolidation_days_min": 3,
    "consolidation_days_max": 7,
}

DESCENDING_TRIANGLE = {
    "require_flat_support": True,
    "require_descending_resistance": True,
}

UPTREND_LINE_BREAK_RETEST = {
    "require_breakout": True,
    "require_successful_retest": True,
}

# --- Entry timing ---

ENTRY_TIMING = {
    "breakout_close": True,
    "retest_pullback": True,
    "retest_max_days": 3,
}

PATTERN_ENTRY_TIMING = {
    "double_bottom": "neckline_break_or_pullback",
    "inverse_head_shoulders": "neckline_break_or_pullback",
    "ascending_flag": "channel_breakout_immediate",
    "ascending_triangle": "resistance_break_with_volume",
    "downtrend_line_break_retest": "retest_required",
    "double_top": "neckline_break_down",
    "head_and_shoulders": "neckline_break_down",
    "descending_flag": "channel_breakdown",
    "descending_triangle": "support_break_down",
    "uptrend_line_break_retest": "retest_required",
}

PATTERN_ENTRY_TIMING_LABELS = {
    "neckline_break_or_pullback": "ネックライン上抜け（終値確定）or 1〜3日後の押し目",
    "channel_breakout_immediate": "チャネル上抜け直後（初動が命）",
    "resistance_break_with_volume": "水平レジスタンス突破＋出来高増加",
    "retest_required": "リテスト成功を確認してからエントリー",
    "neckline_break_down": "ネックライン/サポート下抜け確定（終値ベース）",
    "channel_breakdown": "チャネル下抜け確定",
    "support_break_down": "サポートライン下抜け確定",
}

# --- Exit timing ---

EXIT_TIMING = {
    "target_reached": True,
    "weakness_detected": True,
    "sell_pattern_appeared": True,
}

# --- Time-based stop ---

TIME_STOP = {
    "stagnant_days": 5,
    "sideways_days": 10,
    "force_close_days": 14,
}

# --- Pattern registries (iterable lookup) ---

LONG_PATTERNS = {
    "double_bottom": DOUBLE_BOTTOM,
    "inverse_head_shoulders": INVERSE_HEAD_SHOULDERS,
    "ascending_flag": ASCENDING_FLAG,
    "ascending_triangle": ASCENDING_TRIANGLE,
    "downtrend_line_break_retest": DOWNTREND_LINE_BREAK_RETEST,
}

SHORT_PATTERNS = {
    "double_top": DOUBLE_TOP,
    "head_and_shoulders": HEAD_AND_SHOULDERS,
    "descending_flag": DESCENDING_FLAG,
    "descending_triangle": DESCENDING_TRIANGLE,
    "uptrend_line_break_retest": UPTREND_LINE_BREAK_RETEST,
}
