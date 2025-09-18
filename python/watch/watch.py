# python/watch/watch.py
import argparse
import logging
import random
import sqlite3
import time as time_module
from datetime import datetime, timedelta

import pandas as pd
import requests
import yfinance as yf

from python.config import config
from python.utils.logger import get_logger

# 設定読み込み


logger = get_logger("watch", category="watch")

DB_PATH = config.db_path

__all__ = ["save_data_to_db", "get_price_history", "calc_volatility", "run_realtime_mode", "run_dev_mode"]


# --- データ取得 ---
def get_price_history(code, limit=5):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT price FROM intraday WHERE code = ? ORDER BY timestamp DESC LIMIT ?",
        (code, limit),
    )
    history = [row[0] for row in c.fetchall()][::-1]  # 古い順に並べ替え
    conn.close()
    return history


# --- データ保存 ---
def save_data_to_db(code, timestamp, price, volume):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        if hasattr(timestamp, "strftime"):
            timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        else:
            timestamp_str = str(timestamp)

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS intraday (
                code TEXT,
                timestamp DATETIME,
                price REAL,
                volume INTEGER,
                PRIMARY KEY (code, timestamp)
            )
        """
        )
        c.execute(
            "INSERT OR REPLACE INTO intraday VALUES (?, ?, ?, ?)",
            (code, timestamp_str, price, volume),
        )

        conn.commit()
        logger.info("保存成功: intraday にデータ追加 -> %s %s %.2f %d", code, timestamp_str, price, volume)
    except Exception as e:
        logging.error(f"DB保存エラー: {e}")
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
            logger.info("yfinanceから取得成功: %s -> %s", symbol, price)
            return float(price)
        except Exception as e:
            logger.error("yfinance取得エラー: %s", e)
            # フォールバック: ランダム値
            price = round(random.uniform(1000, 5000), 2)
            logger.warning("フォールバック: ランダム値を使用 %s -> %s", symbol, price)
            return price

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
        response.raise_for_status()
        data = response.json()
        price = float(data.get("price"))
        logger.info("APIから取得成功: %s -> %s", symbol, price)
        return price

    except requests.exceptions.RequestException as e:
        logger.error("API取得エラー: %s", e)
        # フォールバック: yfinance or ランダム
        try:
            ticker = yf.Ticker(f"{symbol}.T")
            price = ticker.history(period="1d")["Close"].iloc[-1]
            logger.info("フォールバック(yfinance): %s -> %s", symbol, price)
            return float(price)
        except Exception:
            price = round(random.uniform(1000, 5000), 2)
            logger.warning("フォールバック: ランダム値を使用 %s -> %s", symbol, price)
            return price


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

            save_data_to_db(code, current_dt, price, volume)

            history = price_history[code]
            history.append(price)
            last_price[code] = price

            # --- 連続下落検知 ---
            if len(history) >= 3 and history[-1] < history[-2] < history[-3]:
                logging.warning(f"{code} 連続下落検出: {history[-3]:.1f} -> {history[-2]:.1f} -> {history[-1]:.1f}")

            # --- ボラティリティ警告(直近5本) ---
            recent_prices = history[-5:]
            vol = calc_volatility(recent_prices)
            if vol > config.volatility_threshold:
                logging.warning(f"{code} ボラティリティ警告: {vol:.2f}%")

            # --- 前回比 -3%以上下落 ---
            if len(history) >= 2:
                drop_pct = (history[-1] - history[-2]) / history[-2] * 100
                if drop_pct <= config.crash_threshold:
                    message = f"{code} 前回比 {config.crash_threshold}%以上下落:\
                                {history[-2]:.1f} -> {history[-1]:.1f} ({drop_pct:.2f}%)"
                    logging.warning(message)
                    from python.utils.alert import send_alert

                    send_alert(message, level="WARNING")

        current_dt += timedelta(minutes=1)
        time_module.sleep(0.5)


# --- 本番リアルタイム監視（2分周期） ---
def run_realtime_mode():
    logging.info("=== リアルタイム監視開始 ===")
    stock_df = pd.read_csv(config.codes_path)
    codes = stock_df["code"].tolist()
    last_price = {code: random.uniform(1000, 2000) for code in codes}  # 仮の前回価格

    while True:
        current_dt = datetime.now()
        for code in codes:
            # 株価取得（API or ランダム）
            price = get_stock_price(code)

            # volume が未定義だったので追加（ランダム値でOK）
            volume = random.randint(100, 1000)

            save_data_to_db(code, current_dt, price, volume)

            history = get_price_history(
                code, limit=config.volatility_period + 2
            )  # ボラティリティ計算に必要な期間+2本分
            if not history:
                history = [price]  # 履歴がない場合は現在の価格のみ

            # --- 連続下落検知 ---
            if len(history) >= 3 and history[-1] < history[-2] < history[-3]:
                logging.warning(f"{code} 連続下落検出: {history[-3]:.1f} -> {history[-2]:.1f} -> {history[-1]:.1f}")

            # --- ボラティリティ警告(直近N本) ---
            recent_prices = history[-config.volatility_period :]
            vol = calc_volatility(recent_prices)
            if vol > config.volatility_threshold:
                logging.warning(f"{code} ボラティリティ警告: {vol:.2f}%")

            # --- 前回比 -3%以上下落 ---
            prev = last_price[code]
            drop_pct = (price - prev) / prev * 100
            if drop_pct <= config.crash_threshold:  # config.crash_threshold を利用
                message = (
                    f"{code} 前回比 {config.crash_threshold}%以上下落: {prev:.1f} -> {price:.1f} ({drop_pct:.2f}%)"
                )
                logging.warning(message)
                from python.utils.alert import send_alert

                send_alert(message, level="WARNING")

            last_price[code] = price

        time_module.sleep(120)  # 2分周期


# --- メイン ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", help="開発モード: 過去日 YYYYMMDD")
    args = parser.parse_args()

    if args.dev:
        run_dev_mode(args.dev)
    else:
        run_realtime_mode()
