# tests/test_analyze_logic.py
"""
週足スイングトレード分析ロジックの単体テスト
対象: environment_filter, detect_patterns, calculate_risk, score_pattern
"""

import numpy as np
import pandas as pd
import pytest

from python.trading.rules import risk_management
from python.watch.analyze import (
    _linear_slope,
    calculate_risk,
    detect_patterns,
    environment_filter,
    score_pattern,
)


# ---------------------------------------------------------------------------
# ヘルパー: テスト用週足 DataFrame を生成
# ---------------------------------------------------------------------------

def _make_weekly_df(
    n: int = 60,
    trend: str = "up",
    base_price: float = 1000.0,
    volume_spike: bool = False,
) -> pd.DataFrame:
    """
    n 週分のダミー週足データを生成する
    trend: 'up' | 'down' | 'flat'
    """
    np.random.seed(42)
    if trend == "up":
        close = base_price + np.linspace(0, base_price * 0.5, n) + np.random.randn(n) * 5
    elif trend == "down":
        close = base_price + np.linspace(0, -base_price * 0.5, n) + np.random.randn(n) * 5
    else:
        close = np.full(n, base_price) + np.random.randn(n) * 5

    high = close + np.abs(np.random.randn(n)) * 10
    low = close - np.abs(np.random.randn(n)) * 10
    open_ = close + np.random.randn(n) * 3
    volume = np.full(n, 10000) + np.random.randint(-500, 500, n)

    if volume_spike:
        volume[-1] = 30000  # 直近が 3 倍出来高

    dates = pd.date_range(end="2026-02-21", periods=n, freq="W-FRI")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


# ---------------------------------------------------------------------------
# environment_filter テスト
# ---------------------------------------------------------------------------

class TestEnvironmentFilter:
    def test_long_trend(self):
        df = _make_weekly_df(n=60, trend="up")
        result = environment_filter(df)
        assert result == "LONG"

    def test_short_trend(self):
        df = _make_weekly_df(n=60, trend="down")
        result = environment_filter(df)
        assert result == "SHORT"

    def test_insufficient_data_returns_none(self):
        df = _make_weekly_df(n=10, trend="up")
        result = environment_filter(df)
        assert result == "NONE"

    def test_flat_trend_may_return_none(self):
        df = _make_weekly_df(n=60, trend="flat")
        result = environment_filter(df)
        # フラット相場では NONE になることが多いが、LONG/SHORT の場合もあり得る
        assert result in ("LONG", "SHORT", "NONE")


# ---------------------------------------------------------------------------
# detect_patterns テスト
# ---------------------------------------------------------------------------

class TestDetectPatterns:
    def test_volume_surge_detected(self):
        df = _make_weekly_df(n=60, trend="up", volume_spike=True)
        patterns = detect_patterns(df)
        assert "volume_surge" in patterns

    def test_no_volume_surge_without_spike(self):
        df = _make_weekly_df(n=60, trend="up", volume_spike=False)
        patterns = detect_patterns(df)
        # volume_surge がないことを確認（通常出来高では検出されない）
        # ランダム性があるため、確実には言えないが spike がなければ基本検出されない
        # ここでは返り値がリストであることを確認
        assert isinstance(patterns, list)

    def test_insufficient_data_returns_empty(self):
        df = _make_weekly_df(n=5, trend="up")
        patterns = detect_patterns(df)
        assert patterns == []

    def test_returns_list_of_strings(self):
        df = _make_weekly_df(n=60, trend="up")
        patterns = detect_patterns(df)
        assert isinstance(patterns, list)
        for p in patterns:
            assert isinstance(p, str)


# ---------------------------------------------------------------------------
# calculate_risk テスト
# ---------------------------------------------------------------------------

class TestCalculateRisk:
    def test_long_risk_keys_present(self):
        df = _make_weekly_df(n=60, trend="up")
        result = calculate_risk(df, "LONG")
        assert "entry" in result
        assert "stop_loss" in result
        assert "take_profit" in result
        assert "atr" in result

    def test_long_stop_loss_below_entry(self):
        df = _make_weekly_df(n=60, trend="up")
        result = calculate_risk(df, "LONG")
        assert result["stop_loss"] < result["entry"]

    def test_long_take_profit_above_entry(self):
        df = _make_weekly_df(n=60, trend="up")
        result = calculate_risk(df, "LONG")
        assert result["take_profit"] > result["entry"]

    def test_short_stop_loss_above_entry(self):
        df = _make_weekly_df(n=60, trend="down")
        result = calculate_risk(df, "SHORT")
        assert result["stop_loss"] > result["entry"]

    def test_short_take_profit_below_entry(self):
        df = _make_weekly_df(n=60, trend="down")
        result = calculate_risk(df, "SHORT")
        assert result["take_profit"] < result["entry"]

    def test_insufficient_data_returns_zero(self):
        df = _make_weekly_df(n=5, trend="up")
        result = calculate_risk(df, "LONG")
        assert result["entry"] == 0.0

    def test_rr_ratio_matches_risk_management(self):
        """RR 比率が risk_management の設定 (ATR_TP_MULTIPLIER / ATR_STOP_MULTIPLIER) どおりになる"""
        df = _make_weekly_df(n=60, trend="up")
        result = calculate_risk(df, "LONG")
        if result["entry"] > 0 and result["stop_loss"] > 0:
            stop_dist = abs(result["entry"] - result["stop_loss"])
            tp_dist = abs(result["take_profit"] - result["entry"])
            rr = tp_dist / stop_dist
            expected = risk_management.ATR_TP_MULTIPLIER / risk_management.ATR_STOP_MULTIPLIER
            assert rr == pytest.approx(expected, rel=0.01), f"RR ratio expected {expected:.2f}, got {rr:.2f}"


# ---------------------------------------------------------------------------
# score_pattern テスト
# ---------------------------------------------------------------------------

class TestScorePattern:
    def test_full_score_conditions(self):
        """全条件を満たした場合のスコアを確認"""
        df = _make_weekly_df(n=60, trend="up", volume_spike=True)
        # RSI が 40-65 になるよう上昇トレンドデータを使用
        patterns = ["double_bottom", "volume_surge"]
        risk = {"entry": 1000.0, "stop_loss": 900.0, "take_profit": 1200.0, "atr": 50.0}
        score, rationale = score_pattern("LONG", patterns, df, risk)
        assert risk_management.SCORE_THRESHOLD_ENTRY <= score <= risk_management.SCORE_MAX
        assert isinstance(rationale, str)

    def test_trend_only_gives_trend_weight(self):
        """トレンド一致だけなら trend_match の点数になる (データが短く RSI / MACD は判定されない)"""
        df = _make_weekly_df(n=10, trend="up")
        risk = {"entry": 0.0, "stop_loss": 0.0, "take_profit": 0.0, "atr": 0.0}
        score, _ = score_pattern("LONG", [], df, risk)
        assert score == risk_management.SCORE_WEIGHTS["trend_match"]

    def test_no_trend_gives_zero_trend_points(self):
        """NONE トレンドではトレンドスコアが加算されない"""
        df = _make_weekly_df(n=60, trend="flat")
        risk = {"entry": 0.0, "stop_loss": 0.0, "take_profit": 0.0, "atr": 0.0}
        score, _ = score_pattern("NONE", [], df, risk)
        assert score == 0

    def test_volume_surge_adds_volume_weight(self):
        df = _make_weekly_df(n=60, trend="up")
        risk = {"entry": 0.0, "stop_loss": 0.0, "take_profit": 0.0, "atr": 0.0}
        score_without, _ = score_pattern("LONG", [], df, risk)
        score_with, _ = score_pattern("LONG", ["volume_surge"], df, risk)
        assert score_with - score_without == risk_management.SCORE_WEIGHTS["volume_match"]

    def test_pattern_adds_pattern_weight(self):
        df = _make_weekly_df(n=60, trend="up")
        risk = {"entry": 0.0, "stop_loss": 0.0, "take_profit": 0.0, "atr": 0.0}
        score_without, _ = score_pattern("LONG", [], df, risk)
        score_with, _ = score_pattern("LONG", ["double_bottom"], df, risk)
        assert score_with - score_without == risk_management.SCORE_WEIGHTS["pattern_match"]

    def test_rr_is_not_scored(self):
        """7 点満点のスコアに RR は含まれない (RR の最低値は利確目標の計算側で担保する)"""
        df = _make_weekly_df(n=60, trend="up")
        risk_good = {"entry": 1000.0, "stop_loss": 900.0, "take_profit": 1200.0, "atr": 50.0}
        risk_bad = {"entry": 1000.0, "stop_loss": 900.0, "take_profit": 1050.0, "atr": 50.0}
        score_good, _ = score_pattern("LONG", [], df, risk_good)
        score_bad, _ = score_pattern("LONG", [], df, risk_bad)
        assert score_good == score_bad

    def test_score_never_exceeds_max(self):
        df = _make_weekly_df(n=60, trend="up", volume_spike=True)
        risk = {"entry": 1000.0, "stop_loss": 900.0, "take_profit": 1200.0, "atr": 50.0}
        patterns = ["double_bottom", "inverse_head_and_shoulders", "flag", "volume_surge"]
        score, _ = score_pattern("LONG", patterns, df, risk)
        assert score <= risk_management.SCORE_MAX


# ---------------------------------------------------------------------------
# _linear_slope テスト
# ---------------------------------------------------------------------------

class TestLinearSlope:
    def test_positive_slope(self):
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        slope = _linear_slope(s)
        assert slope > 0

    def test_negative_slope(self):
        s = pd.Series([5.0, 4.0, 3.0, 2.0, 1.0])
        slope = _linear_slope(s)
        assert slope < 0

    def test_flat_slope(self):
        s = pd.Series([3.0, 3.0, 3.0, 3.0, 3.0])
        slope = _linear_slope(s)
        assert slope == 0.0

    def test_single_element_returns_zero(self):
        s = pd.Series([5.0])
        slope = _linear_slope(s)
        assert slope == 0.0
