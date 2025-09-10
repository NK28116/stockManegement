# python/watch/watch.py
import argparse
import logging

import random
import sqlite3

# 設定読み込み

import time as time_module
from datetime import datetime, timedelta

import pandas as pd

from python.config import config
from python.utils.logger import get_logger

logger = get_logger("watch", category="watch")

DB_PATH = config.db_path

__all__ = ["save_data_to_db", "calc_volatility", "run_realtime_mode", "run_dev_mode"]


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
    except Exception as e:
        logging.error(f"DB保存エラー: {e}")
    conn.commit()
    conn.close()


# --- ボラティリティ計算 ---
def calc_volatility(prices):
    if len(prices) < 2:
        return 0
    return pd.Series(prices).pct_change().std() * 100


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
                if drop_pct <= -3.0:
                    logging.warning(
                        f"{code} 前回比 -3%以上下落: {history[-2]:.1f} -> {history[-1]:.1f} ({drop_pct:.2f}%)"
                    )
                    # 将来 Slack/LINE 通知は alert.py の send_alert() を呼ぶ

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
            # TODO: 証券会社APIなどでリアル株価取得
            price = last_price[code] * (1 + random.uniform(-0.01, 0.01))
            volume = random.randint(100, 1000)

            save_data_to_db(code, current_dt, price, volume)

            # --- 前回比 -3%以上下落 ---
            prev = last_price[code]
            drop_pct = (price - prev) / prev * 100
            if drop_pct <= -3.0:
                logging.warning(f"{code} 前回比 -3%以上下落: {prev:.1f} -> {price:.1f} ({drop_pct:.2f}%)")

            # --- 連続下落・ボラティリティ ---
            # 過去5本の履歴を取得する場合は DB から SELECT するなどで対応可能
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
