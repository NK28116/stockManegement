# ひょっとして使われていない？
import yfinance as yf
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('python/logs/stock_management.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 出力先をdata/analysis_result.txtに
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "../data/analysis_result.txt")

def fetch_stock_data(ticker: str, period="1mo") -> Optional[pd.DataFrame]:
    """
    株価データを取得する
    
    Args:
        ticker: ティッカーシンボル
        period: 取得期間
        
    Returns:
        DataFrame: 株価データ、エラーの場合はNone
    """
    try:
        logger.info(f"株価データ取得開始: {ticker}")
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        
        if df.empty:
            logger.error(f"データが取得できませんでした: {ticker}")
            return None
            
        logger.info(f"株価データ取得完了: {ticker} - {len(df)}件")
        return df
        
    except Exception as e:
        logger.error(f"株価データ取得エラー: {ticker} - {e}")
        return None

def analyze_stock(df: pd.DataFrame) -> List[str]:
    """
    株価データを分析する
    
    Args:
        df: 株価データ
        
    Returns:
        List[str]: 分析結果
    """
    try:
        if df is None or df.empty:
            logger.error("分析対象のデータがありません")
            return ["エラー: 分析対象のデータがありません"]
        
        closes = df["Close"].tolist()
        signals = []
        
        for i in range(1, len(closes)):
            change = "+" if closes[i] > closes[i-1] else "-"
            signals.append(change)
        
        results = []
        buy_price = None  # 買値を記録
        buy_date = None   # 買いの日付

        for i in range(1, len(signals)):
            pattern = signals[i-1] + signals[i]
            # Off-by-one 修正: パターンは signals[i] を含むため、date/price も i+1 を参照
            date = df.index[i+1].strftime("%Y-%m-%d")
            price = closes[i+1]

            if pattern == "++" and buy_price is None:
                # 買いエントリー
                buy_price = price
                buy_date = date
                results.append(f"{date} {price:.2f}円: ++ → 買いエントリー")
            
            elif pattern == "+-":
                results.append(f"{date} {price:.2f}円: +- → 次に++または--が出たら売却")

            elif pattern == "--" and buy_price is not None:
                # 売却
                diff = price - buy_price
                results.append(f"{date} {price:.2f}円: -- → 売却（買値 {buy_price:.2f}円 → 損益 {diff:.2f}円）")
                buy_price = None  # リセット
                buy_date = None

            elif pattern == "++" and buy_price is not None:
                results.append(f"{date} {price:.2f}円: ++ → 継続保持中")

            elif pattern == "+-" and buy_price is not None:
                results.append(f"{date} {price:.2f}円: +- → 継続保持中")

            else:
                results.append(f"{date} {price:.2f}円: 継続 ({pattern})")

        logger.info(f"分析完了: {len(results)}件の結果")
        return results
        
    except Exception as e:
        logger.error(f"分析エラー: {e}")
        return [f"エラー: 分析中に問題が発生しました - {e}"]

def save_results(results: List[str]) -> bool:
    """
    分析結果を保存する
    
    Args:
        results: 分析結果のリスト
        
    Returns:
        bool: 保存が成功したかどうか
    """
    try:
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(f"# 分析結果 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")
            for line in results:
                f.write(line + "\n")
        
        logger.info(f"結果を {OUTPUT_FILE} に保存しました")
        return True
        
    except Exception as e:
        logger.error(f"結果保存エラー: {e}")
        return False

if __name__ == "__main__":
    try:
        ticker = "7203.T"  # トヨタ（例）
        df = fetch_stock_data(ticker)
        if df is not None:
            results = analyze_stock(df)
            if save_results(results):
                print("分析完了")
            else:
                print("結果保存に失敗しました")
        else:
            print("データ取得に失敗しました")
    except Exception as e:
        logger.error(f"メイン処理エラー: {e}")
        print(f"エラーが発生しました: {e}")