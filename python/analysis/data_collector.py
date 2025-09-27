"""
前四半期のデータ取得と分析スクリプト
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import pandas as pd
import psycopg2
import yfinance as yf
from psycopg2 import Error as PgError

from python.config import config
from python.utils.logger import get_logger

logger = get_logger("data_collector", category="analysis")

__all__ = ["main", "StockDataCollector", "get_stock_list_from_db"]


class StockDataCollector:
    def __init__(self):
        self.quarter_start, self.quarter_end = self._get_last_quarter_dates()
        self.four_quarter_start, self.four_quarter_end = self._get_four_quarter_dates()

    def _get_last_quarter_dates(self) -> Tuple[str, str]:
        """前四半期の期間を取得"""
        today = datetime.now()
        # 会計四半期（1-3, 4-6, 7-9, 10-12月）で計算
        current_quarter = (today.month - 1) // 3 + 1
        if current_quarter == 1:
            # 前四半期は前年のQ4
            quarter_end = datetime(today.year - 1, 12, 31)
            quarter_start = datetime(today.year - 1, 10, 1)
        else:
            quarter_end = datetime(today.year, (current_quarter - 1) * 3, 1) - timedelta(days=1)
            quarter_start = datetime(today.year, (current_quarter - 2) * 3 + 1, 1)
        return quarter_start.strftime("%Y-%m-%d"), quarter_end.strftime("%Y-%m-%d")

    def _get_four_quarter_dates(self) -> Tuple[str, str]:
        """直近4四半期の期間を取得"""
        today = datetime.now()
        current_quarter = (today.month - 1) // 3 + 1
        if current_quarter == 1:
            start = datetime(today.year - 1, 1, 1)
            end = datetime(today.year - 1, 12, 31)
        else:
            # 直近4四半期分を today から遡る
            end = datetime(today.year, (current_quarter - 1) * 3, 1) - timedelta(days=1)
            start = datetime(end.year - 1, end.month + 1, 1)
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    def collect_stock_data(self, code: str) -> Optional[Dict]:
        """銘柄データの取得"""
        try:
            # 入力検証
            if not code or code.strip() == "":
                get_logger(f"警告: 無効な銘柄コード: {code}")
                return None

            # .Tが既に含まれているかチェック
            symbol = code.strip()
            if not symbol.endswith(".T"):
                symbol = f"{symbol}.T"

            get_logger(f"データ取得中: {symbol} ({self.quarter_start} - {self.quarter_end})")
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=self.quarter_start, end=self.quarter_end)

            if df.empty:
                get_logger(f"警告: {code}のデータが取得できませんでした（上場廃止または銘柄コードが無効の可能性）")
                return None

            # 最低限のデータが存在するかチェック
            required_columns = ["Open", "High", "Low", "Close", "Volume"]
            if not all(col in df.columns for col in required_columns):
                get_logger(f"警告: {code}の必要な価格データが不足しています")
                return None

            return df  # 取得したDataFrameを返す

        except Exception as e:
            # より詳細なエラーハンドリング
            error_msg = str(e)
            if "404" in error_msg or "not found" in error_msg.lower():
                get_logger(f"エラー: {code}の銘柄が見つかりません（上場廃止の可能性）")
            elif "timeout" in error_msg.lower():
                get_logger(f"エラー: {code}のデータ取得がタイムアウトしました")
            else:
                get_logger(f"エラー: {code}のデータ取得失敗 - {e}")
            return None

    def fetch_and_store_prices(self, code: str, quarter_start: str, quarter_end: str):
        """指定した期間の日次データを取得してDBに保存"""
        conn = None
        try:
            # 過去1年間のデータを取得し、最新のデータのみを更新対象とする
            df = yf.download(code, start=quarter_start, end=quarter_end)
            if df.empty:
                logger.warning(f"データなし: {code}")
                return

            db_config = config.get_db_config()
            conn = psycopg2.connect(**db_config)
            cur = conn.cursor()
            for date, row in df.iterrows():
                # 既存のデータがあれば更新、なければ挿入 (PostgreSQLのUPSERT)
                cur.execute(
                    """
                    INSERT INTO stock_data
                    (code, date, open, high, low, close, volume, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (code, date) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume,
                        created_at = EXCLUDED.created_at
                """,
                    (
                        code,
                        date.strftime("%Y-%m-%d"),
                        row["Open"],
                        row["High"],
                        row["Low"],
                        row["Close"],
                        int(row["Volume"]),
                        datetime.now(),
                    ),
                )
            conn.commit()
            logger.info(f"日次データ取得・保存完了: {code} ({len(df)}件)")
        except PgError as e:
            logger.error(f"エラー: {code} - {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()


def get_stock_list_from_db() -> list:
    """stocks テーブルから銘柄コードリストを取得"""
    conn = None
    try:
        db_config = config.get_db_config()
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        cur.execute("SELECT code FROM stocks")
        codes = [row[0] for row in cur.fetchall()]
        return codes
    except PgError as e:
        logger.error(f"銘柄コード取得エラー: {e}")
        return []
    finally:
        if conn:
            conn.close()


def main(is_test_mode: bool = False):
    collector = StockDataCollector()
    results = []
    codes = get_stock_list_from_db()
    logger.info(f"DBから取得した銘柄数: {len(codes)}")

    for code in codes:
        if not is_test_mode:
            collector.fetch_and_store_prices(code, collector.four_quarter_start, collector.four_quarter_end)
        else:
            logger.info(f"テストモードのため、{code}の日次データ取得・保存はスキップします。")

        stock_df = collector.collect_stock_data(code)
        if stock_df is not None and not stock_df.empty:
            stock_df["コード"] = code
            results.append(stock_df)

    if results:
        final_df = pd.concat(results, ignore_index=True)
        if not is_test_mode:
            output_path = os.path.join(config.data_dir, "quarterly_data_collection.csv")
            os.makedirs(config.data_dir, exist_ok=True)
            final_df.to_csv(output_path, index=False, encoding="utf-8")
            logger.info(f"分析結果を保存しました: {output_path}")
        else:
            logger.info("テストモードのため、分析結果のCSV保存はスキップします。")
            logger.debug(f"分析結果 (テストモード):\n{final_df.to_string()}")
    else:
        logger.warning("分析可能な銘柄データがありません")


if __name__ == "__main__":
    main()
