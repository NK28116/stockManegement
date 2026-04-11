# python/watch/watch.py
import argparse
import logging
import random
import time
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from python.config import config
from python.db.database import get_db_connection  # PostgreSQL接続用に追加
from python.utils.alert import send_alert
from python.utils.logger import get_logger
from python.utils.rules_loader import get_active_rules

# 設定読み込み


logger = get_logger("watch", category="watch")

# DB_PATH = config.db_path # SQLite用なので削除

__all__ = [
    "save_data_to_db",
    "get_price_history",
    "calc_volatility",
    "run_realtime_mode",
    "run_dev_mode",
    "main",
]


def main():
    run_once()


# --- データ取得 ---
def get_price_history(code, limit=5):
    conn = None
    try:
        from sqlalchemy import text

        conn = get_db_connection()
        stmt = text("SELECT price FROM intraday WHERE code = :code ORDER BY timestamp DESC LIMIT :limit")
        result = conn.execute(stmt, {"code": code, "limit": limit})
        history = [row[0] for row in result.fetchall()][::-1]  # 古い順に並べ替え
        return history
    except Exception as e:
        logging.error(f"\n DBデータ取得エラー: {e}\n")
        return []
    finally:
        if conn:
            conn.close()


# --- データ保存 ---
def save_data_to_db(code, timestamp, price, volume):
    conn = None
    try:
        from sqlalchemy import text
        import os

        _db_type = os.getenv("DB_TYPE", "postgresql").lower()

        conn = get_db_connection()
        # Create table if not exists
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS intraday (
                code TEXT,
                timestamp TIMESTAMP,
                price REAL,
                volume INTEGER,
                PRIMARY KEY (code, timestamp)
            )
            """
            )
        )

        if _db_type == "sqlite":
            conn.execute(
                text(
                    """
                INSERT OR REPLACE INTO intraday (code, timestamp, price, volume)
                VALUES (:code, :timestamp, :price, :volume)
                """
                ),
                {"code": code, "timestamp": timestamp, "price": price, "volume": volume},
            )
        else:
            conn.execute(
                text(
                    """
                INSERT INTO intraday (code, timestamp, price, volume)
                VALUES (:code, :timestamp, :price, :volume)
                ON CONFLICT (code, timestamp) DO UPDATE
                SET price = EXCLUDED.price, volume = EXCLUDED.volume
                """
                ),
                {"code": code, "timestamp": timestamp, "price": price, "volume": volume},
            )

        conn.commit()
        logger.info("\n DB保存成功: intraday にデータ追加")
    except Exception as e:
        logging.error(f"\n DB保存エラー: {e}\n")
    finally:
        if conn:
            conn.close()


# --- ボラティリティ計算 ---
def calc_volatility(prices):
    if len(prices) < 2:
        return 0
    return pd.Series(prices).pct_change().std() * 100


def get_stock_price(symbol: str) -> float:
    """
    株価を取得する
    - APIキー未設定 → yfinanceから取得
    - APIキー設定済み → 証券会社APIから取得
    """
    try:
        ticker = yf.Ticker(symbol)
        price = ticker.history(period="1d")["Close"].iloc[-1]
        volume = ticker.history(period="1d")["Volume"].iloc[-1]
        return float(price), int(volume)
    except Exception:
        logger.error(
            f"\n {symbol}: possibly delisted; no price data found (period=1d) "
            '(Yahoo error = "No data found, symbol may be delisted")'
        )
        # フォールバック: ランダム値
        price = round(random.uniform(1000, 5000), 2)
        volume = random.randint(100, 1000)
        logger.warning("\n== フォールバック: ランダム値を使用 %s -> %s==\n", symbol, price)
        return price, volume


# --- 共通処理 ---
def _monitor_stock(
    code,
    current_dt,
    price,
    volume,
    history,
    last_price,
    name=None,
    is_test_mode: bool = False,
):
    """
    監視処理共通化（銘柄ごとにまとめてログ出力）
    """
    if not is_test_mode:
        save_data_to_db(code, current_dt, price, volume)
        logger.info(f"{current_dt.strftime('%Y-%m-%d %H:%M:%S')} - INFO - DB保存成功: intraday にデータ追加")
    else:
        logger.info(
            f"{current_dt.strftime('%Y-%m-%d %H:%M:%S')} - INFO - テストモードのため、DB保存はスキップ: intraday にデータ追加"
        )
    history.append(float(price))

    logs = []
    warnings = []
    ticker = yf.Ticker(code)
    name = ticker.info["shortName"]

    # === INFOログ ===
    if name:
        header = f"\n########## {code} ({name}) ###########"
    else:
        header = f"\n### {code} ###"
    logs.append(header)

    logs.append(f"{current_dt.strftime('%Y-%m-%d %H:%M:%S')} - INFO - 株価取得成功: {code} -> {price}\n")

    # Load rules
    rules = get_active_rules()

    # === 警告系 ===
    if len(history) >= 3 and history[-1] < history[-2] < history[-3]:
        warnings.append(f"- 連続下落検出: {history[-3]:.1f} -> {history[-2]:.1f} -> {history[-1]:.1f}")

    recent_prices = history[-config.volatility_period :]
    if len(recent_prices) >= 2:
        vol = calc_volatility(recent_prices)
        if vol > rules.filters.volatility_threshold:
            warnings.append(f"- ボラティリティ警告: {vol:.2f}%")

    if last_price is not None and last_price > 0:
        drop_pct = (price - last_price) / last_price * 100
        crash_threshold = rules.filters.crash_threshold_percent
        if drop_pct <= crash_threshold:
            warnings.append(
                f"- 前回比 {crash_threshold}%以上下落: {last_price:.1f} -> {price:.1f} ({drop_pct:.2f}%)\n"
            )

    if warnings:
        for warning_msg in warnings:
            logger.warning(f"WARNING: {code} - {warning_msg}")

    return float(price)


# --- 擬似リアルタイム監視(devモード用) ---
def run_dev_mode(dev_date):
    logging.info("=== 開発モード: 過去日の擬似リアルタイム監視 ===")

    stock_df = pd.read_csv(config.codes_path)
    codes = stock_df["code"].tolist()

    start_dt = datetime.strptime(dev_date, "%Y%m%d").replace(hour=10, minute=0)
    end_dt = start_dt + timedelta(minutes=10)
    current_dt = start_dt

    price_history = {code: [random.uniform(1000, 2000)] for code in codes}
    last_price = {code: price_history[code][-1] for code in codes}

    while current_dt <= end_dt:
        for code in codes:
            change_pct = random.uniform(-0.5, 0.5) / 100
            price = last_price[code] * (1 + change_pct)
            volume = random.randint(100, 1000)

            last_price[code] = _monitor_stock(code, current_dt, price, volume, price_history[code], last_price[code])

        current_dt += timedelta(minutes=1)
        time.sleep(0.5)  # time_module.sleep を time.sleep に変更


def load_stock_codes():
    """監視対象コード一覧をCSVから取得"""
    stock_df = pd.read_csv(config.codes_path)
    return stock_df["code"].tolist()


def run_once():
    codes = load_stock_codes()
    current_dt = datetime.now()
    results = []

    for code in codes:
        price, volume = get_stock_price(code)
        history = get_price_history(code, limit=config.volatility_period + 2)
        last_price = history[-1] if history else None

        updated_price = _monitor_stock(code, current_dt, price, volume, history, last_price)
        results.append((code, updated_price, volume))

    return results


def detect_intraday_crash(code, current_price, last_price):
    if last_price is None or last_price == 0:
        return None

    drop_pct = (current_price - last_price) / last_price * 100

    rules = get_active_rules()
    crash_threshold = rules.filters.crash_threshold_percent

    if drop_pct <= crash_threshold:
        message = f"[分足急落] {code}: {last_price:.1f} -> {current_price:.1f} " f"({drop_pct:.2f}%)"
        send_alert(message, level="WARNING")  # Slack に送信
        return message
    return None


def run_once_with_crash_check(is_test_mode: bool = False):
    """分足1回取得＋急落検知"""
    current_codes = load_stock_codes()  # 最新の監視対象コードリストを取得
    current_dt = datetime.now()
    alerts = []

    for code in current_codes:  # 最新のコードリストを使用
        price, volume = get_stock_price(code)
        history = get_price_history(code, limit=3)
        last_price = history[-1] if history else None

        _monitor_stock(
            code,
            current_dt,
            price,
            volume,
            history,
            last_price,
            is_test_mode=is_test_mode,
        )
        alert = detect_intraday_crash(code, price, last_price)
        if alert:
            alerts.append(alert)

    return alerts


def run_realtime_mode():
    """ローカル実行: 2分ごとの無限ループ (市場の開場時間と昼休みを考慮)"""
    while True:
        now = datetime.now()
        current_time = now.time()

        # 市場の開場時間 (9:00 - 11:30, 12:30 - 15:00)
        market_open_morning_start = time.fromisoformat("09:00:00")
        market_open_morning_end = time.fromisoformat("11:30:00")
        market_open_afternoon_start = time.fromisoformat("12:30:00")
        market_open_afternoon_end = time.fromisoformat("15:00:00")

        if (market_open_morning_start <= current_time <= market_open_morning_end) or (
            market_open_afternoon_start <= current_time <= market_open_afternoon_end
        ):
            # 市場開場中
            logger.info("市場開場中: 株価監視を実行します。")
            # 毎回最新の銘柄コードリストを読み込む
            current_codes = load_stock_codes()
            results = []

            for code in current_codes:
                price, volume = get_stock_price(code)
                history = get_price_history(code, limit=config.volatility_period + 2)
                last_price = history[-1] if history else None

                updated_price = _monitor_stock(code, now, price, volume, history, last_price)
                results.append((code, updated_price, volume))
            time.sleep(120)  # 2分待機
        elif market_open_morning_end < current_time < market_open_afternoon_start:
            # 昼休み中
            logger.info("昼休み中: 監視を一時停止し、後場開始まで待機します。")
            # 後場開始までの残り時間を計算
            wait_seconds = (datetime.combine(now.date(), market_open_afternoon_start) - now).total_seconds()
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            else:
                time.sleep(60)  # 念のため1分待機
        else:
            # 市場閉場中 (15:00以降または9:00以前)
            logger.info("市場閉場中: 翌日の開場まで待機します。")
            # 翌日の市場開場までの残り時間を計算
            tomorrow_morning_open = datetime.combine(now.date() + timedelta(days=1), market_open_morning_start)
            wait_seconds = (tomorrow_morning_open - now).total_seconds()
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            else:
                time.sleep(3600)  # 念のため1時間待機 (エラー防止)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", help="開発モード: 過去日 YYYYMMDD")
    args = parser.parse_args()

    if args.dev:
        run_dev_mode(args.dev)
    else:
        run_realtime_mode()
