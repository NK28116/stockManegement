# python/watch/analyze.py

import json
import logging
import time
from datetime import date
from typing import Dict, List, Tuple

import pandas as pd
import ta
import yfinance as yf

from python.config import config
from python.db.database import get_db_connection, get_db_session
from python.db.models import Signal
from python.trading.rules import indicator_settings, risk_management, swing_trade_rules
from python.utils.alert import send_alert
from python.utils.indicators import (
    calculate_bollinger_bands,
    calculate_macd,
    calculate_rsi,
)
from python.utils.rules_loader import get_active_rules

logger = logging.getLogger("analyze")

# 週足トレンド判定用MA期間（週足40週 ≈ 日足200日に相当）
_WEEKLY_MA_PERIOD = 40
_ATR_PERIOD = indicator_settings.ATR_PERIOD
_ATR_STOP_MULTIPLIER = risk_management.ATR_STOP_MULTIPLIER
_ATR_TP_MULTIPLIER = risk_management.ATR_TP_MULTIPLIER
_VOLUME_MA_PERIOD = indicator_settings.VOLUME_MA_PERIOD_LONG
_SCORE_THRESHOLD = risk_management.SCORE_THRESHOLD_ENTRY
_RSI_PERIOD = indicator_settings.RSI_PERIOD
_RSI_LONG_RANGE = indicator_settings.RSI_LONG_RANGE
_RSI_SHORT_RANGE = indicator_settings.RSI_SHORT_RANGE


def get_daily_price_data(code: str, limit: int = 100) -> pd.DataFrame:
    """
    指定された銘柄の日足データを取得する
    Args:
        code: 銘柄コード
        limit: 取得件数
    Returns:
        DataFrame: 日足データ (index=date, columns=[open, high, low, close, volume])
    """
    query = f"""
        SELECT date, open, high, low, close, volume
        FROM daily_data
        WHERE code = '{code}'
        ORDER BY date ASC
    """
    if limit:
        query = f"""
            SELECT * FROM (
                SELECT date, open, high, low, close, volume
                FROM daily_data
                WHERE code = '{code}'
                ORDER BY date DESC
                LIMIT {limit}
            ) as sub
            ORDER BY date ASC
        """

    try:
        conn = get_db_connection()
        df = pd.read_sql_query(query, conn, index_col="date", parse_dates=["date"])
        conn.close()
        return df
    except Exception as e:
        logger.error(f"日足データ取得エラー ({code}): {e}")
        return pd.DataFrame()


def get_weekly_price_data(symbol: str, period: str = "2y") -> pd.DataFrame:
    """
    yfinance で週足データを取得する
    Args:
        symbol: 銘柄コード (例: '7203.T')
        period: 取得期間 (例: '2y')
    Returns:
        DataFrame: 週足 OHLCV データ
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval="1wk")
        if df.empty:
            logger.warning(f"週足データが空: {symbol}")
            return pd.DataFrame()
        df.columns = [c.lower() for c in df.columns]
        return df
    except Exception as e:
        logger.error(f"週足データ取得エラー ({symbol}): {e}")
        return pd.DataFrame()


def environment_filter(df: pd.DataFrame) -> str:
    """
    40週移動平均線でトレンド方向を判定する
    Args:
        df: 週足 OHLCV DataFrame (close 列必須)
    Returns:
        'LONG' | 'SHORT' | 'NONE'
    """
    if len(df) < _WEEKLY_MA_PERIOD + 2:
        return "NONE"

    close = df["close"]
    ma40 = close.rolling(window=_WEEKLY_MA_PERIOD).mean()

    current_close = close.iloc[-1]
    current_ma = ma40.iloc[-1]
    prev_ma = ma40.iloc[-2]

    if pd.isna(current_ma) or pd.isna(prev_ma):
        return "NONE"

    slope = current_ma - prev_ma

    if current_close > current_ma and slope > 0:
        return "LONG"
    if current_close < current_ma and slope < 0:
        return "SHORT"
    return "NONE"


def detect_patterns(df: pd.DataFrame) -> List[str]:
    """
    チャートパターンと出来高増加を検出する
    Args:
        df: 週足 OHLCV DataFrame
    Returns:
        検出されたパターン名のリスト
    """
    patterns: List[str] = []

    if len(df) < _VOLUME_MA_PERIOD + 1:
        return patterns

    close = df["close"]
    volume = df["volume"]

    # --- 出来高増加判定 ---
    vol_ma20 = volume.rolling(window=_VOLUME_MA_PERIOD).mean()
    current_vol = volume.iloc[-1]
    avg_vol = vol_ma20.iloc[-1]
    if not pd.isna(avg_vol) and avg_vol > 0 and current_vol > avg_vol:
        patterns.append("volume_surge")

    # --- ダブルボトム (簡易判定) ---
    # 直近20本の安値で、最近の安値2点が近い水準にある場合
    if len(close) >= 20:
        window = close.tail(20)
        low_window = df["low"].tail(20)
        local_mins_idx = _find_local_minima(low_window)
        if len(local_mins_idx) >= 2:
            last_two = local_mins_idx[-2:]
            p1 = low_window.iloc[last_two[0]]
            p2 = low_window.iloc[last_two[1]]
            # 2点が5%以内の差なら W 底
            if abs(p1 - p2) / p1 < 0.05:
                patterns.append("double_bottom")

    # --- 逆三尊 (簡易判定) ---
    if len(close) >= 30:
        low_window = df["low"].tail(30)
        local_mins_idx = _find_local_minima(low_window)
        if len(local_mins_idx) >= 3:
            last_three = local_mins_idx[-3:]
            p1 = low_window.iloc[last_three[0]]
            p2 = low_window.iloc[last_three[1]]
            p3 = low_window.iloc[last_three[2]]
            # 中央が最も低く、両端が近い水準 → 逆三尊
            if p2 < p1 and p2 < p3 and abs(p1 - p3) / p1 < 0.05:
                patterns.append("inverse_head_and_shoulders")

    # --- フラッグ (簡易判定: 直近の高値・安値が収縮傾向) ---
    if len(close) >= 10:
        recent = close.tail(10)
        high_range = df["high"].tail(10).max() - df["low"].tail(10).min()
        prev_range = (
            df["high"].iloc[-20:-10].max() - df["low"].iloc[-20:-10].min()
            if len(df) >= 20
            else None
        )
        if prev_range is not None and prev_range > 0 and high_range / prev_range < 0.6:
            patterns.append("flag")

    # --- トライアングル (簡易判定: 高値切り下げ・安値切り上げ) ---
    if len(close) >= 15:
        highs = df["high"].tail(15)
        lows = df["low"].tail(15)
        high_slope = _linear_slope(highs)
        low_slope = _linear_slope(lows)
        if high_slope < -0.001 and low_slope > 0.001:
            patterns.append("triangle")

    return patterns


def _find_local_minima(series: pd.Series) -> List[int]:
    """系列内の局所最小値のインデックス（位置）リストを返す"""
    result = []
    values = series.values
    for i in range(1, len(values) - 1):
        if values[i] < values[i - 1] and values[i] < values[i + 1]:
            result.append(i)
    return result


def _linear_slope(series: pd.Series) -> float:
    """系列の線形近似スロープを返す"""
    n = len(series)
    if n < 2:
        return 0.0
    x = list(range(n))
    x_mean = sum(x) / n
    y_mean = series.mean()
    numerator = sum((x[i] - x_mean) * (series.iloc[i] - y_mean) for i in range(n))
    denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return 0.0
    return numerator / denominator


def calculate_risk(df: pd.DataFrame, trend: str) -> Dict[str, float]:
    """
    ATR(14) を使ってストップロス・利確目標を計算する
    Args:
        df: 週足 OHLCV DataFrame
        trend: 'LONG' | 'SHORT'
    Returns:
        {'entry': float, 'stop_loss': float, 'take_profit': float, 'atr': float}
    """
    default = {"entry": 0.0, "stop_loss": 0.0, "take_profit": 0.0, "atr": 0.0}

    if len(df) < _ATR_PERIOD + 1:
        return default

    try:
        atr_indicator = ta.volatility.AverageTrueRange(
            high=df["high"],
            low=df["low"],
            close=df["close"],
            window=_ATR_PERIOD,
        )
        atr_series = atr_indicator.average_true_range()
        atr = float(atr_series.iloc[-1])
    except Exception as e:
        logger.error(f"ATR 計算エラー: {e}")
        return default

    entry = float(df["close"].iloc[-1])
    stop_distance = atr * _ATR_STOP_MULTIPLIER
    tp_distance = atr * _ATR_TP_MULTIPLIER

    if trend == "LONG":
        return {
            "entry": entry,
            "stop_loss": entry - stop_distance,
            "take_profit": entry + tp_distance,
            "atr": atr,
        }
    if trend == "SHORT":
        return {
            "entry": entry,
            "stop_loss": entry + stop_distance,
            "take_profit": entry - tp_distance,
            "atr": atr,
        }
    return default


def score_pattern(
    trend: str,
    patterns: List[str],
    df: pd.DataFrame,
    risk: Dict[str, float],
) -> Tuple[int, str]:
    """
    スコア基準 (python/trading/rules/risk_management.py SCORE_WEIGHTS):
        パターン成立 +2
        出来高条件   +1
        RSI 一致     +1
        MACD 一致    +1
        トレンド一致 +2
    合計 7 点満点、SCORE_THRESHOLD_ENTRY 点以上を有効シグナルとする
    """
    weights = risk_management.SCORE_WEIGHTS
    score = 0
    reasons: List[str] = []

    # トレンド一致
    if trend in ("LONG", "SHORT"):
        w = weights["trend_match"]
        score += w
        reasons.append(f"トレンド一致({trend}): +{w}")

    # パターン成立 (volume_surge以外のチャートパターン)
    structural_patterns = [p for p in patterns if p != "volume_surge"]
    if structural_patterns:
        w = weights["pattern_match"]
        score += w
        reasons.append(f"パターン検出({','.join(structural_patterns)}): +{w}")

    # 出来高条件
    if "volume_surge" in patterns:
        w = weights["volume_match"]
        score += w
        reasons.append(f"出来高条件: +{w}")

    # RSI 一致
    if len(df) >= _RSI_PERIOD + 1:
        rsi_series = calculate_rsi(df["close"], period=_RSI_PERIOD)
        rsi_val = float(rsi_series.iloc[-1]) if not rsi_series.empty else None
        if rsi_val is not None and not pd.isna(rsi_val):
            lo_long, hi_long = _RSI_LONG_RANGE
            lo_short, hi_short = _RSI_SHORT_RANGE
            if trend == "LONG" and lo_long <= rsi_val <= hi_long:
                w = weights["rsi_match"]
                score += w
                reasons.append(f"RSI適正({rsi_val:.1f}): +{w}")
            elif trend == "SHORT" and lo_short <= rsi_val <= hi_short:
                w = weights["rsi_match"]
                score += w
                reasons.append(f"RSI適正({rsi_val:.1f}): +{w}")

    # MACD 一致 (トレンド方向と整合するクロス状態)
    macd_long_period = max(
        indicator_settings.MACD_FAST_PERIOD,
        indicator_settings.MACD_SLOW_PERIOD,
    )
    if len(df) >= macd_long_period + indicator_settings.MACD_SIGNAL_PERIOD + 1:
        macd_df = calculate_macd(
            df["close"],
            short_period=indicator_settings.MACD_FAST_PERIOD,
            long_period=indicator_settings.MACD_SLOW_PERIOD,
            signal_period=indicator_settings.MACD_SIGNAL_PERIOD,
        )
        if len(macd_df) >= 1:
            macd_val = float(macd_df.iloc[-1]["MACD"])
            signal_val = float(macd_df.iloc[-1]["Signal"])
            if trend == "LONG" and macd_val > signal_val:
                w = weights["macd_match"]
                score += w
                reasons.append(f"MACD陽転: +{w}")
            elif trend == "SHORT" and macd_val < signal_val:
                w = weights["macd_match"]
                score += w
                reasons.append(f"MACD陰転: +{w}")

    return score, " / ".join(reasons)


def _get_entry_timing(patterns: List[str], trend: str) -> str:
    """検出パターンに基づく推奨エントリータイミングを返す"""
    labels = swing_trade_rules.PATTERN_ENTRY_TIMING_LABELS
    mapping = swing_trade_rules.PATTERN_ENTRY_TIMING
    lines: List[str] = []

    for p in patterns:
        if p == "volume_surge":
            continue
        key = mapping.get(p)
        if key and key in labels:
            lines.append(f"[{p}] {labels[key]}")

    if not lines:
        if trend == "LONG":
            lines.append("ブレイク当日の終値確定 or 1〜3日後のリテスト押し目")
        else:
            lines.append("ブレイク下抜け確定（終値ベース）or 1〜3日後の戻り売り")

    lines.append("※出来高が直近5日平均の1.2倍以上あること")
    direction = "購入" if trend == "LONG" else "売却"
    return f"【{direction}推奨タイミング】\n" + "\n".join(lines)


def _get_exit_guidance(trend: str) -> str:
    """ポジション方向に応じた利確/損切りガイダンスを返す"""
    ts = swing_trade_rules.TIME_STOP
    if trend == "LONG":
        return (
            "【利確/撤退ガイド】\n"
            f"① 目標到達: RR 1.5倍 or 直近高値\n"
            f"② 弱さ検知: RSI 70→低下 / 上ヒゲ連発 / 出来高減少+上昇\n"
            f"③ 売りパターン出現: ダブルトップ・三尊 → 即撤退\n"
            f"④ 時間損切り: {ts['stagnant_days']}日伸びず→一部撤退 / "
            f"{ts['sideways_days']}日横ばい→全撤退 / "
            f"{ts['force_close_days']}日→強制クローズ検討"
        )
    return (
        "【利確/撤退ガイド】\n"
        f"① 目標到達: RR 1.5倍 or 直近安値\n"
        f"② 弱さ検知: RSI 30→反発 / 下ヒゲ連発 / 出来高減少+下落\n"
        f"③ 買いパターン出現: ダブルボトム・逆三尊 → 即撤退\n"
        f"④ 時間損切り: {ts['stagnant_days']}日伸びず→一部撤退 / "
        f"{ts['sideways_days']}日横ばい→全撤退 / "
        f"{ts['force_close_days']}日→強制クローズ検討"
    )


def analyze_daily_data(code: str, name: str, is_test_mode: bool = False):
    """
    日足データを分析し、シグナルが出ていれば通知する
    """
    logger.info(f"Analyzing daily data for {code} ({name})...")

    df = get_daily_price_data(code, limit=100)
    if df.empty or len(df) < 2:
        logger.warning(f"データ不足のため分析スキップ: {code}")
        return

    rules = get_active_rules()

    crash_threshold = config.crash_threshold

    current_price = df.iloc[-1]["close"]
    prev_price = df.iloc[-2]["close"]

    change_rate = (current_price - prev_price) / prev_price * 100

    if change_rate <= crash_threshold:
        msg = f"⚠️ 【急落注意】{name} ({code}) が前日比 {change_rate:.2f}% 下落しました (現在値: {current_price})"
        send_alert(msg, level="WARNING")
        logger.warning(msg)

    macd_df = calculate_macd(
        df["close"],
        short_period=rules.indicators.macd.fast_period,
        long_period=rules.indicators.macd.slow_period,
        signal_period=rules.indicators.macd.signal_period,
    )

    if len(macd_df) >= 2:
        curr_macd = macd_df.iloc[-1]["MACD"]
        curr_signal = macd_df.iloc[-1]["Signal"]
        prev_macd = macd_df.iloc[-2]["MACD"]
        prev_signal = macd_df.iloc[-2]["Signal"]

        if prev_macd <= prev_signal and curr_macd > curr_signal:
            logger.info(f"MACDゴールデンクロス検知: {name} ({code})")

    bb_df = calculate_bollinger_bands(
        df["close"],
        period=rules.indicators.bollinger.period,
        num_std=rules.indicators.bollinger.std,
    )

    if len(bb_df) >= 1:
        curr_close = df.iloc[-1]["close"]
        upper = bb_df.iloc[-1]["Upper"]
        lower = bb_df.iloc[-1]["Lower"]

        if curr_close > upper:
            logger.info(f"ボリンジャーバンド アッパーバンド突破: {name} ({code})")
        elif curr_close < lower:
            logger.info(f"ボリンジャーバンド ローワーバンド下抜け: {name} ({code})")


def _analyze_weekly_swing(symbol: str) -> None:
    """
    1 銘柄の週足スイングトレード分析を実行し、signals テーブルへ保存する
    """
    df = get_weekly_price_data(symbol)
    if df.empty:
        logger.warning(f"データ取得失敗: {symbol} (空データ)")
        return
    if len(df) < _WEEKLY_MA_PERIOD + 2:
        logger.warning(
            f"データ不足のため週足分析スキップ: {symbol} "
            f"(取得行数={len(df)}, 必要行数={_WEEKLY_MA_PERIOD + 2})"
        )
        return
    logger.info(f"データ取得成功: {symbol} (取得行数={len(df)})")

    trend = environment_filter(df)
    if trend == "NONE":
        logger.info(f"トレンド不明のためスキップ: {symbol}")
        _save_signal(symbol, "NONE", 0, [], 0.0, 0.0, "トレンド不明")
        return

    patterns = detect_patterns(df)
    risk = calculate_risk(df, trend)
    score, rationale = score_pattern(trend, patterns, df, risk)

    if score >= _SCORE_THRESHOLD:
        entry_timing = _get_entry_timing(patterns, trend)
        exit_guidance = _get_exit_guidance(trend)
        rationale = f"{rationale}\n---\n{entry_timing}\n{exit_guidance}"

    threshold_status = (
        "有効シグナル"
        if score >= _SCORE_THRESHOLD
        else f"閾値未達(閾値={_SCORE_THRESHOLD})"
    )
    logger.info(
        f"[{symbol}] trend={trend} score={score}/{risk_management.SCORE_MAX} "
        f"[{threshold_status}] patterns={patterns}"
    )

    _save_signal(
        symbol=symbol,
        signal_type=trend if score >= _SCORE_THRESHOLD else "NONE",
        score=score,
        patterns=patterns,
        stop_loss=risk.get("stop_loss", 0.0),
        take_profit=risk.get("take_profit", 0.0),
        rationale=rationale,
    )


def _save_signal(
    symbol: str,
    signal_type: str,
    score: int,
    patterns: List[str],
    stop_loss: float,
    take_profit: float,
    rationale: str,
) -> None:
    """分析結果を signals テーブルへ保存する"""
    try:
        with get_db_session() as session:
            record = Signal(
                symbol=symbol,
                analysis_date=date.today(),
                signal_type=signal_type,
                score=score,
                detected_patterns=json.dumps(patterns, ensure_ascii=False),
                stop_loss=stop_loss,
                take_profit=take_profit,
                rationale=rationale,
            )
            session.add(record)
            session.commit()
            logger.info(f"シグナル保存: {symbol} {signal_type} score={score}")
    except Exception as e:
        logger.error(f"シグナル保存エラー ({symbol}): {e}")


def main() -> None:
    """
    登録銘柄の週足スイングトレード分析エントリーポイント
    """
    logger.info("週足スイングトレード分析 開始")

    try:
        stock_df = pd.read_csv(config.codes_path)
    except Exception as e:
        logger.error(f"銘柄リスト読み込みエラー: {e}")
        return

    logger.info(f"分析対象銘柄数: {len(stock_df)}")

    for _, row in stock_df.iterrows():
        symbol = str(row["code"])
        try:
            _analyze_weekly_swing(symbol)
        except Exception as e:
            logger.error(f"週足分析エラー ({symbol}): {e}", exc_info=True)
        # yfinance レートリミット回避のため銘柄間に 1 秒ウェイト
        time.sleep(1)

    logger.info("週足スイングトレード分析 完了")
