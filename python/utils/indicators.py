# python/utils/indicator.py
# MACD, Bollinger Bands を計算する
from typing import Tuple

import pandas as pd


def calculate_macd(
    prices: pd.Series,
    short_period: int = 12,
    long_period: int = 26,
    signal_period: int = 9,
) -> pd.DataFrame:
    """
    MACD を計算する
    Args:
        prices: 株価シリーズ（終値）
        short_period: 短期EMA期間
        long_period: 長期EMA期間
        signal_period: シグナルラインEMA期間
    Returns:
        DataFrame: MACD, シグナル, ヒストグラム
    """
    ema_short = prices.ewm(span=short_period, adjust=False).mean()
    ema_long = prices.ewm(span=long_period, adjust=False).mean()
    macd = ema_short - ema_long
    signal = macd.ewm(span=signal_period, adjust=False).mean()
    histogram = macd - signal
    df = pd.DataFrame({"MACD": macd, "Signal": signal, "Histogram": histogram})
    return df


__all__ = ["calculate_bollinger_bands"]


def calculate_bollinger_bands(prices: pd.Series, period: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    """
    ボリンジャーバンドを計算する
    Args:
        prices: 株価シリーズ（終値）
        period: 移動平均期間
        num_std: 標準偏差の係数
    Returns:
        DataFrame: 移動平均(MA), 上部バンド(Upper), 下部バンド(Lower)
    """
    ma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper = ma + (std * num_std)
    lower = ma - (std * num_std)
    df = pd.DataFrame({"MA": ma, "Upper": upper, "Lower": lower})
    return df


# --- テスト用 ---
if __name__ == "__main__":
    import numpy as np

    # ダミー終値データ
    np.random.seed(0)
    prices = pd.Series(100 + np.random.randn(50).cumsum())

    macd_df = calculate_macd(prices)
    print("=== MACD ===")
    print(macd_df.tail())

    bb_df = calculate_bollinger_bands(prices)
    print("\n=== Bollinger Bands ===")
    print(bb_df.tail())
