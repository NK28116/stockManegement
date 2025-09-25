import pandas as pd
import psycopg2
from psycopg2 import Error as PgError

from python.config import config
from python.db.database import get_db_connection
from ..utils.alert import send_alert
from python.utils.indicators import (  # インジケーター計算関数をインポート
    calculate_bollinger_bands,
    calculate_macd,
)
from python.utils.logger import get_logger
from pathlib import Path
import json

logger = get_logger("analyze", category="watch")

__all__ = ["analyze_daily_data", "analyze_minute_data"]


# フラグ保存用の一時ファイルディレクトリ
FLAG_DIR = Path("data/crash_flags")
FLAG_DIR.mkdir(parents=True, exist_ok=True)


def save_intraday_crash_flag(code: str, date: pd.Timestamp):
    """分足急落フラグを保存"""
    flag_file = FLAG_DIR / f"{code}_{date.strftime('%Y%m%d')}.json"
    with open(flag_file, "w") as f:
        json.dump({"crash": True}, f)


def check_intraday_crash_flag(code: str, date: pd.Timestamp) -> bool:
    """当日分足急落があったか確認"""
    flag_file = FLAG_DIR / f"{code}_{date.strftime('%Y%m%d')}.json"
    return flag_file.exists()


def get_intraday_price_data(code, limit_minutes=60):  # 15分足作成に必要な分足データを取得するため、多めに取得
    """DBから指定銘柄の分足データを取得する"""
    conn = None
    try:
        conn = get_db_connection()
        # 最新のデータから指定された期間の分足データを取得
        query = "SELECT date, open, high, low, close, volume \
                FROM stock_data \
                WHERE code = %s \
                ORDER BY date DESC LIMIT %s"
        # 15分足を作成するために、limit_minutes * 1分足データが必要
        # 例えば、60分間のデータがあれば、4つの15分足が作成できる
        df = pd.read_sql_query(query, conn, params=(code, limit_minutes), index_col="date", parse_dates=["date"])
        # 取得したデータを時系列順に並べ替える
        df = df.sort_index(ascending=True)
        return df
    except PgError as e:
        logger.error(f"DBから分足データ取得エラー: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()


def analyze_minute_data(code: str, name: str):
    """指定された銘柄の15分足データを分析し急落検知やテクニカル指標に基づく警告を行う

    Args:
        code (str): 分析対象の銘柄コード
    """
    logger.info(f"{name}( {code}) の15分足データ分析を開始")
    # 15分足を作成するために、過去60分間の分足データを取得
    df_minute = get_intraday_price_data(code, limit_minutes=60)

    if df_minute.empty:
        logger.warning(f"{name}( {code}) の分足データが見つかりませんでした。")
        return

    # 分足データを15分足にリサンプリング
    # '15T'は15分間隔を意味する
    # open, high, low, close, volumeを適切に集約
    df = (
        df_minute.resample("15T")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .dropna()
    )  # データがない15分足は除外

    if df.empty:
        logger.warning(f"{name} ({code}) の15分足データが作成できませんでした。")
        return

    # --- 15分足での急落検知 ---
    # ユーザーの要件「16分前(watch8回)から15分足を作りその日の急落を警告」を考慮し、
    # 直近の15分足と、その1つ前の15分足を比較する
    if len(df) >= 2:
        prev_close = df["close"].iloc[-2]
        current_close = df["close"].iloc[-1]
        drop_pct = (current_close - prev_close) / prev_close * 100
        if drop_pct <= config.crash_threshold:
            message = (
                f"{name} ({code}) 15分足で {config.crash_threshold}%以上下落: "
                f"{prev_close:.1f} -> {current_close:.1f} ({drop_pct:.2f}%)"
            )
            logger.warning(message)
            from python.utils.alert import send_alert

            send_alert(message, level="WARNING")

            # 🚨 フラグ保存（当日分足急落あり）
            save_intraday_crash_flag(code, df.index[-1])

    # --- MACD分析 ---
    if len(df) >= config.macd_long_period:  # MACD計算に必要な期間
        df = calculate_macd(df)
        # MACDゴールデンクロス/デッドクロスなどの分析ロジックをここに追加
        # 例: MACDがシグナルを上抜けた/下抜けた
        if df["macd"].iloc[-1] > df["macd_signal"].iloc[-1] and df["macd"].iloc[-2] <= df["macd_signal"].iloc[-2]:
            logger.info(f"{name} ({code}) MACDゴールデンクロス発生")
        elif df["macd"].iloc[-1] < df["macd_signal"].iloc[-1] and df["macd"].iloc[-2] >= df["macd_signal"].iloc[-2]:
            logger.info(f"{name} ({code}) MACDデッドクロス発生")

    # --- ボリンジャーバンド分析 ---
    if len(df) >= config.bollinger_period:  # ボリンジャーバンド計算に必要な期間
        df = calculate_bollinger_bands(df)
        # ボリンジャーバンドのブレイクアウトなどの分析ロジックをここに追加
        # 例: 終値がアッパーバンドを上抜けた
        if df["close"].iloc[-1] > df["upper_band"].iloc[-1]:
            logger.info(f"{name} ({code}) ボリンジャーバンドのアッパーバンドを上抜け")
        elif df["close"].iloc[-1] < df["lower_band"].iloc[-1]:
            logger.info(f"{name} ({code}) ボリンジャーバンドのローワーバンドを下抜け")


def get_daily_price_data(code, limit=config.volatility_period + 20):  # MACD/BB計算用に多めに取得
    """DBから指定銘柄の日足データを取得する"""
    conn = None
    try:
        conn = get_db_connection()
        query = "SELECT date, open, high, low, close, volume \
                FROM stock_data \
                WHERE code = %s \
                ORDER BY date ASC LIMIT %s"
        df = pd.read_sql_query(query, conn, params=(code, limit), index_col="date", parse_dates=["date"])
        return df
    except PgError as e:
        logger.error(f"DBから日足データ取得エラー: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()


def analyze_daily_data(code: str, name: str):
    """
    指定された銘柄の日足データを分析し、急落検知やテクニカル指標に基づく警告を行う

    Args:
        code (str): 分析対象の銘柄コード
    """
    logger.info(f"{name} ({code}) の日足データ分析を開始")
    df = get_daily_price_data(code)

    if df.empty:
        logger.warning(f"{name} ({code}) の日足データが見つかりませんでした。")
        return

    # --- 前日比急落検知 ---
    if len(df) >= 2:
        prev_close = df["close"].iloc[-2]
        current_close = df["close"].iloc[-1]
        drop_pct = (current_close - prev_close) / prev_close * 100
        if drop_pct <= config.crash_threshold:
            intraday_flag = check_intraday_crash_flag(code, df.index[-1])
            if intraday_flag:
                # 🚨 分足でも日中に急落あり → 強い警告
                message = (
                    f"{name} ({code}) 終値で急落確定！（日中にも急落発生）: "
                    f"{prev_close:.1f} -> {current_close:.1f} ({drop_pct:.2f}%)"
                )
                send_alert(message, level="CRITICAL")
                logger.error(message)
            else:
                # 日足だけ急落 → 通常警告
                message = (
                    f"{name} ({code}) 日足で {config.crash_threshold}%以上下落: "
                    f"{prev_close:.1f} -> {current_close:.1f} ({drop_pct:.2f}%)"
                )
                send_alert(message, level="WARNING")
                logger.warning(message)

    # --- MACD分析 ---
    if len(df) >= config.macd_long_period:  # MACD計算に必要な期間
        df = calculate_macd(df)
        # MACDゴールデンクロス/デッドクロスなどの分析ロジックをここに追加
        # 例: MACDがシグナルを上抜けた/下抜けた
        if df["macd"].iloc[-1] > df["macd_signal"].iloc[-1] and df["macd"].iloc[-2] <= df["macd_signal"].iloc[-2]:
            logger.info(f"{name} ({code}) MACDゴールデンクロス発生")
        elif df["macd"].iloc[-1] < df["macd_signal"].iloc[-1] and df["macd"].iloc[-2] >= df["macd_signal"].iloc[-2]:
            logger.info(f"{name} ({code}) MACDデッドクロス発生")

    # --- ボリンジャーバンド分析 ---
    if len(df) >= config.bollinger_period:  # ボリンジャーバンド計算に必要な期間
        df = calculate_bollinger_bands(df)
        # ボリンジャーバンドのブレイクアウトなどの分析ロジックをここに追加
        # 例: 終値がアッパーバンドを上抜けた
        if df["close"].iloc[-1] > df["upper_band"].iloc[-1]:
            logger.info(f"{name} ({code}) ボリンジャーバンドのアッパーバンドを上抜け")
        elif df["close"].iloc[-1] < df["lower_band"].iloc[-1]:
            logger.info(f"{name} ({code}) ボリンジャーバンドのローワーバンドを下抜け")

    logger.info(f"{name} ({code}) の日足データ分析を完了")


if __name__ == "__main__":
    # 例: my_stock.csv に記載された全銘柄を分析
    stock_df = pd.read_csv(config.codes_path)
    codes = stock_df["code"].tolist()
    for code in codes:
        analyze_daily_data(code)
        analyze_minute_data(code)
