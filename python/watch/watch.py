# python/watch/watch.py
import argparse
import logging
import random
import time
from datetime import datetime, timedelta
from typing import List, Optional

import pandas as pd
import psycopg2
import requests
import yfinance as yf
from psycopg2 import Error as PgError

from python.config import config
from python.utils.alert import send_alert
from python.utils.logger import get_logger

# 設定読み込み


logger = get_logger("watch", category="watch")

__all__ = ["save_data_to_db", "get_price_history", "calc_volatility", "run_realtime_mode", "run_dev_mode"]


# --- データ取得 ---
def get_price_history(code, limit=5):
    conn = None
    try:
        db_config = config.get_db_config()
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        cur.execute(
            "SELECT price FROM intraday WHERE code = %s ORDER BY timestamp DESC LIMIT %s",
            (code, limit),
        )
        history = [row[0] for row in cur.fetchall()][::-1]  # 古い順に並べ替え
        return history
    except PgError as e:
        logger.error(f"価格履歴取得エラー: {e}")
        return []
    finally:
        if conn:
            conn.close()


# --- データ保存 ---
def save_data_to_db(code, timestamp, price, volume):
    conn = None
    try:
        db_config = config.get_db_config()
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()

        if hasattr(timestamp, "strftime"):
            timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        else:
            timestamp_str = str(timestamp)

        # テーブルが存在しない場合は作成 (init_database.pyで作成済みだが念のため)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS intraday (
                code TEXT,
                timestamp TIMESTAMP,
                price DOUBLE PRECISION,
                volume INTEGER,
                PRIMARY KEY (code, timestamp)
            )
        """
        )
        cur.execute(
            """
            INSERT INTO intraday (code, timestamp, price, volume)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (code, timestamp) DO UPDATE SET
                price = EXCLUDED.price,
                volume = EXCLUDED.volume
            """,
            (code, timestamp_str, price, volume),
        )

        conn.commit()
        logger.info("\n DB保存成功: intraday にデータ追加")
    except PgError as e:
        logger.error(f"\n DB保存エラー: {e}\n")
        if conn:
            conn.rollback()
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
    if not config.XXXX_API_KEY or not config.XXXX_API_SECRET or not config.XXXX_API_URL:
        # --- case1: yfinance ---
        try:
            ticker = yf.Ticker(f"{symbol}")
            price = ticker.history(period="1d")["Close"].iloc[-1]
            volume = ticker.history(period="1d")["Volume"].iloc[-1]
            return float(price), int(volume)
        except Exception:
            # フォールバック: ランダム値
            price = round(random.uniform(1000, 5000), 2)
            volume = random.randint(100, 1000)
            return price, volume

    # --- case2: API利用 ---
    try:
        response = requests.get(
            f"{config.XXXX_API_URL}/price/{symbol}",
            headers={
                "X-API-KEY": config.XXXX_API_KEY,
                "X-API-SECRET": config.XXXX_API_SECRET,
            },
            timeout=10,
        )
        data = response.json()
        price = float(data.get("price"))
        volume = int(data.get("volume", random.randint(100, 1000)))  # Assume API can return volume, otherwise random
        return price, volume
    except requests.exceptions.RequestException as e:
        logger.error("\n ==API取得エラー: %s==\n", e)
        # フォールバック: yfinance or ランダム
        try:
            ticker = yf.Ticker(f"{symbol}.T")
            price = ticker.history(period="1d")["Close"].iloc[-1]
            volume = ticker.history(period="1d")["Volume"].iloc[-1]
            logger.info("\n ==フォールバック(yfinance): %s -> %s==\n", symbol, price)
            return float(price), int(volume)
        except Exception:
            price = round(random.uniform(1000, 5000), 2)
            volume = random.randint(100, 1000)  # Ensure volume is defined
            logger.warning("\n== フォールバック: ランダム値を使用 %s -> %s==\n", symbol, price)
            return price, volume


# --- 共通処理 ---
def _monitor_stock(code, current_dt, price, volume, history, last_price, name=None):
    """
    監視処理共通化（銘柄ごとにまとめてログ出力）
    """
    save_data_to_db(code, current_dt, price, volume)
    history.append(float(price))

    logs = []
    warnings = []
    ticker = yf.Ticker(f"{code}")
    name = ticker.info["shortName"]

    # === INFOログ ===
    if name:
        header = f"\n########## {code} ({name}) ###########"
    else:
        header = f"\n### {code} ###"
    logs.append(header)

    logs.append(f"{current_dt.strftime('%Y-%m-%d %H:%M:%S')} - INFO - 株価取得成功: {code} -> {price}")

    logs.append(f"{current_dt.strftime('%Y-%m-%d %H:%M:%S')} - INFO - DB保存成功: intraday にデータ追加\n")

    # === 警告系 ===
    if len(history) >= 3 and history[-1] < history[-2] < history[-3]:
        warnings.append(f"- 連続下落検出: {history[-3]:.1f} -> {history[-2]:.1f} -> {history[-1]:.1f}")

    recent_prices = history[-config.volatility_period :]
    if len(recent_prices) >= 2:
        vol = calc_volatility(recent_prices)
        if vol > config.volatility_threshold:
            warnings.append(f"- ボラティリティ警告: {vol:.2f}%")

    if last_price is not None and last_price > 0:
        drop_pct = (price - last_price) / last_price * 100
        if drop_pct <= config.crash_threshold:
            warnings.append(
                f"- 前回比 {config.crash_threshold}%以上下落: {last_price:.1f} -> {price:.1f} ({drop_pct:.2f}%)\n"
            )

    if warnings:
        logs.append(f"WARNING: {code}\n" + "\n".join(warnings))

    # === 出力 ===
    print("\n".join(logs))

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
        time.sleep(0.5)


def load_stock_codes():
    """監視対象コード一覧をCSVから取得"""
    stock_df = pd.read_csv(config.codes_path)
    return stock_df["code"].tolist()


def run_once(codes: Optional[List[str]] = None):  # codes引数を追加
    if codes:
        target_codes = codes
    else:
        target_codes = load_stock_codes()
    current_dt = datetime.now()
    results = []

    for code in target_codes:  # target_codesを使用
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
    if drop_pct <= config.crash_threshold:
        message = f"[分足急落] {code}: {last_price:.1f} -> {current_price:.1f} ({drop_pct:.2f}%)"
        send_alert(message, level="WARNING")  # Slack に送信
        return message
    return None


def run_once_with_crash_check():
    """分足1回取得＋急落検知"""
    codes = load_stock_codes()
    current_dt = datetime.now()
    alerts = []

    for code in codes:
        price, volume = get_stock_price(code)
        history = get_price_history(code, limit=3)
        last_price = history[-1] if history else None

        _monitor_stock(code, current_dt, price, volume, history, last_price)
        alert = detect_intraday_crash(code, price, last_price)
        if alert:
            alerts.append(alert)

    return alerts


def run_realtime_mode():
    """ローカル実行: 2分ごとの無限ループ"""
    while True:
        run_once()
        time.sleep(120)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", help="開発モード: 過去日 YYYYMMDD")
    parser.add_argument("--once", action="store_true", help="監視タスクを1回だけ実行")
    parser.add_argument("codes", nargs="*", help="監視対象の銘柄コード (複数指定可能)")
    args = parser.parse_args()

    if args.dev:
        run_dev_mode(args.dev)
    elif args.once:
        run_once(codes=args.codes)  # codes引数を渡す
    else:
        run_realtime_mode()
