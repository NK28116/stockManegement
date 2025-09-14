"""
前四半期のデータ取得と分析スクリプト
"""

import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import pandas as pd
import yfinance as yf

from python.config import config
from python.utils.logger import get_logger

logger = get_logger("data_collector", category="analysis")

__all__ = ["main", "StockDataCollector", "get_stock_list_from_db", "fetch_and_store_stock_prices_quarter"]


class StockDataCollector:
    def __init__(self):
        self.quarter_start, self.quarter_end = self._get_last_quarter_dates()
        self.four_quarter_start, self.four_quarter_end = self._get_four_quarter_date()

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

    def _get_four_quarter_date(self) -> Tuple[str, str]:
        """前四半期*4の期間を取得"""
        today = datetime.now()
        # 会計四半期（1-3, 4-6, 7-9, 10-12月）で計算
        # 今月の四半期
        current_quarter = (today.month - 1) // 3 + 1
        if current_quarter == 1:
            # 今がQ1は前年のQ1~Q4
            four_quarter_end = datetime(today.year - 1, 12, 31)
            four_quarter_start = datetime(today.year - 1, 1, 1)
            # 今がQ2ならQ1+前年のQ2,Q3,Q4
        elif current_quarter == 2:
            four_quarter_end = datetime(today.year - 1, 3, 31)
            four_quarter_start = datetime(today.year - 1, 4, 1)
            # 今がQ3ならQ1~Q3+前年のQ4
        elif current_quarter == 3:
            four_quarter_end = datetime(today.year - 1, 6, 30)
            four_quarter_start = datetime(today.year - 1, 7, 1)
            # 今がQ4ならQ1~Q4
        else:
            current_quarter == 4
        four_quarter_end = datetime(today.year - 1, 9, 30)
        four_quarter_start = datetime(today.year - 1, 10, 1)

        return four_quarter_end.strftime("%Y-%m-%d"), four_quarter_start.strftime("%Y-%m-%d")

    def collect_stock_data(self, code: str) -> Optional[Dict]:
        """銘柄データの取得"""
        try:
            # 入力検証
            if not code or code.strip() == "":
                get_logger("警告: 無効な銘柄コード: {code}")
                return None

            # .Tが既に含まれているかチェック
            symbol = code.strip()
            if not symbol.endswith(".T"):
                symbol = "{symbol}.T"

            get_logger("データ取得中: {symbol} ({self.quarter_start} - {self.quarter_end})")
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=self.quarter_start, end=self.quarter_end)

            if df.empty:
                get_logger("警告: {code}のデータが取得できませんでした（上場廃止または銘柄コードが無効の可能性）")
                return None

            # 最低限のデータが存在するかチェック
            required_columns = ["Open", "High", "Low", "Close", "Volume"]
            if not all(col in df.columns for col in required_columns):
                get_logger("警告: {code}の必要な価格データが不足しています")
                return None

            # テクニカル指標を計算してからパフォーマンス分析
            df_with_indicators = self.calculate_indicators(df)
            if df_with_indicators is None:
                return None

            return self.analyze_performance(df_with_indicators)

        except Exception as e:
            # より詳細なエラーハンドリング
            error_msg = str(e)
            if "404" in error_msg or "not found" in error_msg.lower():
                get_logger("エラー: {code}の銘柄が見つかりません（上場廃止の可能性）")
            elif "timeout" in error_msg.lower():
                get_logger("エラー: {code}のデータ取得がタイムアウトしました")
            else:
                get_logger("エラー: {code}のデータ取得失敗 - {e}")
            return None

    def fetch_and_store_prices(self, code: str, quarter_start: str, quarter_end: str):
        """指定した期間の日次データを取得してDBに保存"""
        try:
            # 過去1年間のデータを取得し、最新のデータのみを更新対象とする
            df = yf.download(code, start=quarter_start, end=quarter_end)
            if df.empty:
                logger.warning("データなし: {code}")
                return

            conn = sqlite3.connect(config.db_path)
            cur = conn.cursor()
            for date, row in df.iterrows():
                # 既存のデータがあれば更新、なければ挿入
                cur.execute(
                    """
                    INSERT OR REPLACE INTO stock_data
                    (code, date, open, high, low, close, volume, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
            conn.close()
            logger.info("日次データ取得・保存完了: {code} ({len(df)}件)")
        except Exception as e:
            logger.error("エラー: {code} - {e}")

    def calculate_indicators(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """テクニカル指標の計算"""
        if "Close" not in df.columns:
            get_logger("エラー: データフレームに'Close'列が存在しません")
            return None

        try:
            df["Daily_Return"] = df["Close"].pct_change()
            df["SMA_20"] = df["Close"].rolling(window=20).mean()
            df["Volatility"] = df["Daily_Return"].rolling(window=20).std()
            return df
        except Exception as e:
            get_logger("エラー: テクニカル指標の計算に失敗しました - {e}")
            return None

    # ここじゃない？analyze_my_stock.pyに移す

    # def analyze_performance(
    #     self,
    #     df: pd.DataFrame,
    # ) -> Dict:
    #     """指定した期間のパフォーマンス分析"""
    #     if df is None or df.empty or len(df) == 0:
    #         return {}

    #     try:
    #         # データの有効性をチェック
    #         if len(df) < 1:
    #             return {}

    #         # 価格データの計算
    #         open_value = df["Open"].iloc[0] if not pd.isna(df["Open"].iloc[0]) else None
    #         close_value = df["Close"].iloc[-1] if not pd.isna(df["Close"].iloc[-1]) else None

    #         # 価格変化率の計算（ゼロ除算対策）
    #         price_change = None
    #         if open_value and close_value and open_value != 0:
    #             price_change = (close_value - open_value) / open_value * 100

    #         # 統計値の安全な計算
    #         high_max = df["High"].max() if not df["High"].isna().all() else None
    #         low_min = df["Low"].min() if not df["Low"].isna().all() else None
    #         volume_mean = df["Volume"].mean() if not df["Volume"].isna().all() else None
    #         volatility_mean = (
    #             df["Volatility"].mean() if "Volatility" in df.columns and not df["Volatility"].isna().all() else None
    #         )

    #         return {
    #             "開始日": self.quarter_start,
    #             "終了日": self.quarter_end,
    #             "始値": round(float(open_value), 2) if open_value is not None else None,
    #             "終値": (round(float(close_value), 2) if close_value is not None else None),
    #             "価格変化率(%)": (round(float(price_change), 2) if price_change is not None else None),
    #             "最高値": round(float(high_max), 2) if high_max is not None else None,
    #             "最安値": round(float(low_min), 2) if low_min is not None else None,
    #             "出来高平均": int(volume_mean) if volume_mean is not None else None,
    #             "ボラティリティ": (round(float(volatility_mean), 4) if volatility_mean is not None else None),
    #             "データポイント数": len(df),
    #         }
    #     except Exception as e:
    #         get_logger("エラー: パフォーマンス分析に失敗しました - {e}")
    #         return {}


def get_stock_list_from_db() -> list:
    """stocks テーブルから銘柄コードリストを取得"""
    conn = sqlite3.connect(config.db_path)
    cur = conn.cursor()
    cur.execute("SELECT code FROM stocks")
    codes = [row[0] for row in cur.fetchall()]
    conn.close()
    return codes


# get_stock_list_from_db()->collect_stock_data()->fetch_and_store_stock_prices_quarter+fetch_and_store_daily_prices
def main():
    """メイン処理"""
    collector = StockDataCollector()
    results = []
    # DBから銘柄コードを取得
    codes = get_stock_list_from_db()
    get_logger("DBから取得した銘柄数: {len(codes)}")
    # 各coedsごとに1年前から今日までのデータを取得
    for code in codes:
        data_collection = collector.fetch_and_store_stock_prices(
            code, collector.four_quarter_start, collector.four_quarter_end
        )
        if data_collection:
            data_collection["コード"] = code
            results.append(data_collection)

    # visualizxationに渡すためにCSVに保存

    if results:
        output_path = os.path.join(config.output_dir, "quarterly_data_collection.csv")
        os.makedirs(config.output_dir, exist_ok=True)
        pd.DataFrame(results).to_csv(output_path, index=False, encoding="utf-8")
        get_logger("\n分析結果を保存しました: {output_path}")
    else:
        get_logger("分析可能な銘柄データがありませんでした")
    # 銘柄一覧の読み込み
    if not os.path.exists(codes):
        get_logger("エラー: 銘柄一覧ファイルが存在しません: {codes}")
        return

    try:
        codes_df = pd.read_csv(codes)
        get_logger("銘柄一覧を読み込みました: {len(codes_df)}銘柄")
    except Exception as e:
        get_logger("エラー: 銘柄一覧ファイルの読み込みに失敗しました: {e}")
        return

    # 各銘柄のデータを処理
    successful_count = 0
    for i, row in codes_df.iterrows():
        get_logger("処理中 ({i+1}/{len(codes_df)}): {row['code']} - {row.get('name', '')}")

        stock_data = collector.collect_stock_data(row["code"])
        if stock_data is None:
            continue

        data_collection = dict(stock_data)
        data_collection["コード"] = row["code"]
        data_collection["銘柄名"] = row.get("name", "")
        results.append(data_collection)
        successful_count += 1

    # 結果の保存
    if results:
        output_path = os.path.join(config.output_dir, "quarterly_data_collection.csv")
        os.makedirs(config.output_dir, exist_ok=True)
        pd.DataFrame(results).to_csv(output_path, index=False, encoding="utf-8")
        get_logger("\n分析結果を保存しました: {output_path}")
        get_logger("成功: {successful_count}/{len(codes_df)} 銘柄")
    else:
        get_logger("\n警告: 分析できる銘柄データがありませんでした")


if __name__ == "__main__":
    main()
