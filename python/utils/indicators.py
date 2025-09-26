# python/utils/indicator.py
# MACD, Bollinger Bands を計算する
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


__all__ = ["calculate_bollinger_bands", "detect_sharp_decline"]


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


def detect_sharp_decline(prices: pd.Series, decline_threshold: float = 0.05, period: int = 1) -> pd.DataFrame:
    """
    急落を検出する
    Args:
        prices: 株価シリーズ（終値）
        decline_threshold: 急落と判断する下落率 (例: 0.05 = 5%)
        period: 比較対象とする期間 (例: 1 = 前日比)
    Returns:
        DataFrame: 急落した日付と下落率
    """
    if len(prices) <= period:
        return pd.DataFrame(columns=["Date", "DeclineRate"])

    # 期間ごとの変化率を計算
    # prices.shift(period) は period 日前の価格
    # (prices - prices.shift(period)) / prices.shift(period) で変化率
    decline_rates = (prices.diff(period) / prices.shift(period)).dropna()

    # 急落を検出
    sharp_declines = decline_rates[decline_rates < -decline_threshold]

    if sharp_declines.empty:
        return pd.DataFrame(columns=["Date", "DeclineRate"])

    # 結果をDataFrameに整形
    result_df = pd.DataFrame(
        {
            "Date": sharp_declines.index.strftime("%Y-%m-%d"),
            "DeclineRate": sharp_declines.apply(lambda x: f"{x:.2%}"),
        }
    )
    return result_df


# --- テスト用 ---
if __name__ == "__main__":
    import numpy as np

    # ダミー終値データ
    np.random.seed(0)
    prices = pd.Series(
        100 + np.random.randn(50).cumsum(), index=pd.to_datetime(pd.date_range(start="2023-01-01", periods=50))
    )

    macd_df = calculate_macd(prices)
    print("=== MACD ===")
    print(macd_df.tail())

    bb_df = calculate_bollinger_bands(prices)
    print("\n=== Bollinger Bands ===")
    print(bb_df.tail())

    sharp_decline_df = detect_sharp_decline(prices, decline_threshold=0.02)
    print("\n=== Sharp Declines ===")
    print(sharp_decline_df)
