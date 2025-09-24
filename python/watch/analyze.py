import sqlite3
from typing import List  # Listをインポート

import pandas as pd

from python.config import config
from python.utils.indicators import (  # インジケーター計算関数をインポート
    calculate_bollinger_bands,
    calculate_macd,
)
from python.utils.logger import get_logger

logger = get_logger("analyze", category="watch")

DB_PATH = config.db_path

__all__ = ["analyze_daily_data", "get_high_volatility_stocks"]


def get_daily_price_data(code, limit=config.volatility_period + 20):  # MACD/BB計算用に多めに取得
    """DBから指定銘柄の日足データを取得する"""
    conn = sqlite3.connect(DB_PATH)
    query = f"SELECT date, open, high, low, close, volume \
            FROM stock_data \
            WHERE code = '{code}' \
            ORDER BY date ASC LIMIT {limit}"
    df = pd.read_sql_query(query, conn, index_col="date", parse_dates=["date"])
    conn.close()
    return df


def analyze_daily_data(code: str) -> List[str]:  # 戻り値の型ヒントを変更
    """
    指定された銘柄の日足データを分析し、急落検知やテクニカル指標に基づく警告を行う

    Args:
        code (str): 分析対象の銘柄コード
    Returns:
        List[str]: シグナルが出た銘柄コードのリスト
    """
    logger.info(f"銘柄 {code} の日足データ分析を開始")
    signals = []  # シグナルが出た銘柄コードを格納するリスト

    df = get_daily_price_data(code)

    if df.empty:
        logger.warning(f"銘柄 {code} の日足データが見つかりませんでした。")
        return signals  # データがない場合は空リストを返す

    # --- 前日比急落検知 ---
    if len(df) >= 2:
        prev_close = df["close"].iloc[-2]
        current_close = df["close"].iloc[-1]
        drop_pct = (current_close - prev_close) / prev_close * 100
        if drop_pct <= config.crash_threshold:
            message = (
                f"銘柄 {code} 日足で {config.crash_threshold}%以上下落: "
                f"{prev_close:.1f} -> {current_close:.1f} ({drop_pct:.2f}%)"
            )
            logger.warning(message)
            from python.utils.alert import send_alert

            send_alert(message, level="WARNING")
            signals.append(code)  # シグナルが出た銘柄コードを追加

    # --- MACD分析 ---
    if len(df) >= config.macd_long_period:  # MACD計算に必要な期間
        df = calculate_macd(df)
        # MACDゴールデンクロス/デッドクロスなどの分析ロジックをここに追加
        # 例: MACDがシグナルを上抜けた/下抜けた
        if df["macd"].iloc[-1] > df["macd_signal"].iloc[-1] and df["macd"].iloc[-2] <= df["macd_signal"].iloc[-2]:
            logger.info(f"銘柄 {code} MACDゴールデンクロス発生")
            signals.append(code)  # シグナルが出た銘柄コードを追加
        elif df["macd"].iloc[-1] < df["macd_signal"].iloc[-1] and df["macd"].iloc[-2] >= df["macd_signal"].iloc[-2]:
            logger.info(f"銘柄 {code} MACDデッドクロス発生")
            signals.append(code)  # シグナルが出た銘柄コードを追加

    # --- ボリンジャーバンド分析 ---
    if len(df) >= config.bollinger_period:  # ボリンジャーバンド計算に必要な期間
        df = calculate_bollinger_bands(df)
        # ボリンジャーバンドのブレイクアウトなどの分析ロジックをここに追加
        # 例: 終値がアッパーバンドを上抜けた
        if df["close"].iloc[-1] > df["upper_band"].iloc[-1]:
            logger.info(f"銘柄 {code} ボリンジャーバンドのアッパーバンドを上抜け")
            signals.append(code)  # シグナルが出た銘柄コードを追加
        elif df["close"].iloc[-1] < df["lower_band"].iloc[-1]:
            logger.info(f"銘柄 {code} ボリンジャーバンドのローワーバンドを下抜け")
            signals.append(code)  # シグナルが出た銘柄コードを追加

    logger.info(f"銘柄 {code} の日足データ分析を完了")
    return list(set(signals))  # 重複を排除して返す


def get_high_volatility_stocks() -> List[str]:
    """
    ボラティリティが高い銘柄のリストを取得する
    Returns:
        List[str]: ボラティリティが高い銘柄コードのリスト
    """
    logger.info("高ボラティリティ銘柄の検出を開始")
    high_volatility_codes = []
    stock_df = pd.read_csv(config.codes_path)
    codes = stock_df["code"].tolist()

    for code in codes:
        df = get_daily_price_data(code, limit=config.volatility_period)  # ボラティリティ計算に必要な期間のデータを取得
        if df.empty or len(df) < config.volatility_period:
            continue

        # 終値の対数リターンの標準偏差をボラティリティとする
        # または、単純な日次リターンの標準偏差
        df["daily_return"] = df["close"].pct_change()
        volatility = df["daily_return"].std() * (252**0.5) * 100  # 年率換算、パーセンテージ
        # config.volatility_threshold は日次ボラティリティの閾値として定義されていると仮定

        if volatility > config.volatility_threshold:
            high_volatility_codes.append(code)
            logger.info(f"高ボラティリティ銘柄検出: {code} (ボラティリティ: {volatility:.2f}%)")

    logger.info(f"高ボラティリティ銘柄の検出を完了。検出数: {len(high_volatility_codes)}")
    return high_volatility_codes


if __name__ == "__main__":
    # 例: my_stock.csv に記載された全銘柄を分析
    stock_df = pd.read_csv(config.codes_path)
    codes = stock_df["code"].tolist()
    all_signals = []
    for code in codes:
        all_signals.extend(analyze_daily_data(code))
    import json

    unique_signals = list(set(all_signals))
    print(json.dumps(unique_signals))  # JSON形式で出力
