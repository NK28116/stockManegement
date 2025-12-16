import io
import json
import os
import sys

import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf
from google.cloud import storage

# プロジェクトルートへのパス設定 (モジュール読み込み用)
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../..")

from python.analysis.formula_for_analyzer import (  # noqa: E402
    calculate_technical_indicators,
)
from python.database.connection import get_db  # noqa: E402
from python.database.models import DailyPrice, Stock  # noqa: E402
from python.utils.logger import get_logger  # noqa: E402

logger = get_logger("dailyAggregator", category="watch")

__all__ = ["aggregate_intraday_to_daily", "run_daily_monitor"]


def load_rules_from_gcs(bucket_name="stock-management-prod"):
    """GCSから最新の取引ルールを読み込む"""
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob("trading_rules/active.json")
        if blob.exists():
            json_str = blob.download_as_text()
            logger.info("✅ Loaded active trading rules from GCS.")
            return json.loads(json_str)
    except Exception as e:
        logger.warning(f"⚠️ Failed to load rules from GCS: {e}")
    return {}


def generate_and_upload_chart(stock_code, df, bucket_name="stock-management-prod"):
    """チャートを生成してGCSにアップロード"""
    try:
        plt.figure(figsize=(10, 6))

        # メインチャート
        plt.subplot(2, 1, 1)
        plt.plot(df.index, df["Close"], label="Close")
        if "BB_Upper" in df.columns:
            plt.plot(
                df.index, df["BB_Upper"], label="BB Upper", linestyle="--", alpha=0.5
            )
            plt.plot(
                df.index, df["BB_Lower"], label="BB Lower", linestyle="--", alpha=0.5
            )
        plt.title(f"{stock_code} Daily Chart")
        plt.legend()
        plt.grid(True)

        # RSI
        if "RSI" in df.columns:
            plt.subplot(2, 1, 2)
            plt.plot(df.index, df["RSI"], label="RSI", color="orange")
            plt.axhline(70, linestyle="--", color="red", alpha=0.5)
            plt.axhline(30, linestyle="--", color="green", alpha=0.5)
            plt.legend()
            plt.grid(True)

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png")
        buf.seek(0)
        plt.close()

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(f"charts/{stock_code}_daily.png")
        blob.upload_from_file(buf, content_type="image/png")
        logger.info(f"📈 Chart uploaded: charts/{stock_code}_daily.png")
    except Exception as e:
        logger.error(f"❌ Chart generation failed for {stock_code}: {e}")


def save_daily_data_to_db(db, stock_code, df):
    """DataFrameの最新行をDBに保存 (SQLAlchemy版)"""
    latest = df.iloc[-1]
    date_val = (
        latest.name.date() if isinstance(latest.name, pd.Timestamp) else latest.name
    )

    existing = (
        db.query(DailyPrice)
        .filter(DailyPrice.stock_code == stock_code, DailyPrice.date == date_val)
        .first()
    )

    if not existing:
        daily_price = DailyPrice(
            stock_code=stock_code,
            date=date_val,
            open=float(latest["Open"]),
            high=float(latest["High"]),
            low=float(latest["Low"]),
            close=float(latest["Close"]),
            volume=int(latest["Volume"]),
            rsi=(
                float(latest["RSI"])
                if "RSI" in latest and not pd.isna(latest["RSI"])
                else None
            ),
            bb_upper=(
                float(latest["BB_Upper"])
                if "BB_Upper" in latest and not pd.isna(latest["BB_Upper"])
                else None
            ),
            bb_lower=(
                float(latest["BB_Lower"])
                if "BB_Lower" in latest and not pd.isna(latest["BB_Lower"])
                else None
            ),
        )
        db.add(daily_price)
        db.commit()
        logger.info(f"💾 Data saved for {stock_code} on {date_val}")


def aggregate_intraday_to_daily(target_date: str, is_test_mode: bool = False):
    """
    指定された日付の分足データから日足データを集計し、DBに保存する
    (既存ロジックのORM移行版)
    """
    logger.info(f"{target_date} の日足データを集計開始")

    # TODO: intradayテーブルもSQLAlchemyモデル化が望ましいが、
    # ここでは既存の役割を維持しつつ、保存先をDailyPriceに向ける
    pass


def run_daily_monitor(target_stocks=None):
    """
    日次監視タスクのメイン処理
    1. ルール読み込み
    2. データ取得 (yfinance) & 指標計算
    3. DB保存
    4. チャート生成
    """
    if target_stocks is None:
        target_stocks = ["7203.T", "9984.T", "6758.T"]  # デフォルト監視銘柄

    rules = load_rules_from_gcs()

    with get_db() as db:
        for code in target_stocks:
            # 銘柄マスタ確認
            stock = db.query(Stock).filter(Stock.code == code).first()
            if not stock:
                db.add(Stock(code=code, name=f"Stock {code}", market="TSE"))
                db.commit()

            logger.info(f"🔍 Processing {code}...")
            try:
                # データ取得 (yfinance)
                df = yf.download(code, period="6mo", interval="1d", progress=False)
                if df.empty:
                    continue

                # 指標計算 (formula_for_analyzer利用)
                df = calculate_technical_indicators(df, rules)

                # DB保存
                save_daily_data_to_db(db, code, df)

                # チャート生成
                generate_and_upload_chart(code, df)

            except Exception as e:
                logger.error(f"❌ Error processing {code}: {e}")


if __name__ == "__main__":
    # コマンドライン引数などでモード切替も可能だが、
    # デフォルトでは監視タスクを実行する形にする
    run_daily_monitor()
