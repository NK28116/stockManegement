# python/analysis/formula_for_analyzer.py
"""
テクニカル指標計算と売買シグナル判定
PortfolioAnalyzer や trading で再利用可能
"""

from typing import List, Dict
import pandas as pd
import ta
from python.config import config

__all__ = ["calculate_technical_indicators", "check_buy_signal", "check_sell_signal"]


def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    株価データにテクニカル指標を追加
    Daily Return, SMA20, Volatility, Bollinger Bands, MACD など
    """
    df = df.copy()

    # 日次リターン
    df["Daily_Return"] = df["Close"].pct_change()

    # 単純移動平均(SMA)
    df["SMA_20"] = df["Close"].rolling(window=20).mean()

    # ボラティリティ
    df["Volatility"] = df["Daily_Return"].rolling(window=20).std()

    # Bollinger Bands
    bb = ta.volatility.BollingerBands(close=df["Close"], window=20, window_dev=2)
    df["BB_Middle"] = bb.bollinger_mavg()
    df["BB_Upper"] = bb.bollinger_hband()
    df["BB_Lower"] = bb.bollinger_lband()

    # MACD
    macd = ta.trend.MACD(close=df["Close"])
    df["MACD"] = macd.macd()
    df["MACD_Signal"] = macd.macd_signal()
    df["MACD_Diff"] = macd.macd_diff()

    # RSI
    rsi = ta.momentum.RSIIndicator(close=df["Close"])
    df["RSI"] = rsi.rsi()

    return df


def check_buy_signal(df: pd.DataFrame) -> List[Dict]:
    """
    買いシグナル判定
    条件例:
        - ゴールデンクロス (短期MAが長期MAを上抜け)
        - RSI30以下の反転
        - 価格安値圏 (SMA20の90%以下)
    """
    signals = []
    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]

        # ゴールデンクロス
        if prev["Close"] < prev["SMA_20"] and row["Close"] > row["SMA_20"]:
            signals.append({"date": row.name, "signal": "golden_cross", "price": row["Close"]})
            continue

        # RSI過売り
        if prev["RSI"] < config.rsi_oversold_threshold and row["RSI"] >= config.rsi_oversold_threshold:
            signals.append({"date": row.name, "signal": "rsi_oversold", "price": row["Close"]})
            continue

        # 価格安値圏
        if row["Close"] <= 0.9 * row["SMA_20"]:
            signals.append({"date": row.name, "signal": "price_low", "price": row["Close"]})
            continue

    return signals


def check_sell_signal(df: pd.DataFrame, buy_price: float) -> List[Dict]:
    """
    売りシグナル判定
    条件例:
        - デッドクロス (短期MAが長期MAを下抜け)
        - RSI70以上の反転
        - 利確/ストップロス
    """
    signals = []
    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]

        # デッドクロス
        if prev["Close"] > prev["SMA_20"] and row["Close"] < row["SMA_20"]:
            signals.append({"date": row.name, "signal": "dead_cross", "price": row["Close"]})
            continue

        # RSI過買い
        if prev["RSI"] > config.rsi_overbought_threshold and row["RSI"] <= config.rsi_overbought_threshold:
            signals.append({"date": row.name, "signal": "rsi_overbought", "price": row["Close"]})
            continue

        # 利確
        if buy_price is not None and row["Close"] >= buy_price * (1 + config.take_profit_percent):
            signals.append({"date": row.name, "signal": "take_profit", "price": row["Close"]})
            continue

        # ストップロス
        if buy_price is not None and row["Close"] <= buy_price * (1 - config.stop_loss_percent):
            signals.append({"date": row.name, "signal": "stop_loss", "price": row["Close"]})
            continue

    return signals


def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    株価データに対してテクニカル指標を追加
    - SMA20
    - Bollinger Bands
    - MACD
    """
    df = df.copy()
    df["sma20"] = df["Close"].rolling(window=20).mean()

    # Bollinger Bands
    df["bb_std"] = df["Close"].rolling(window=20).std()
    df["bb_upper"] = df["sma20"] + 2 * df["bb_std"]
    df["bb_lower"] = df["sma20"] - 2 * df["bb_std"]
    df["bb_middle"] = df["sma20"]

    # MACD
    exp12 = df["Close"].ewm(span=12, adjust=False).mean()
    exp26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["macd"] = exp12 - exp26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_dif"] = df["macd"] - df["macd_signal"]

    return df


def generate_buy_sell_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    テクニカル指標から売買シグナルを生成
    - ゴールデンクロス/デッドクロス
    - Bollinger Bands 上抜け/下抜け
    """
    df = df.copy()
    df["signal"] = "HOLD"

    # シンプルMACDクロス判定
    df.loc[(df["macd"] > df["macd_signal"]) & (df["macd"].shift(1) <= df["macd_signal"].shift(1)), "signal"] = "BUY"
    df.loc[(df["macd"] < df["macd_signal"]) & (df["macd"].shift(1) >= df["macd_signal"].shift(1)), "signal"] = "SELL"

    # Bollinger Band 判定（任意で併用可能）
    df.loc[df["Close"] > df["bb_upper"], "signal"] = "SELL"
    df.loc[df["Close"] < df["bb_lower"], "signal"] = "BUY"

    return df
