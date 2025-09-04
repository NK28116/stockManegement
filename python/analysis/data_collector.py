"""
前四半期のデータ取得と分析スクリプト
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
from typing import Tuple, Dict, Optional
from pathlib import Path

# プロジェクトルートをパスに追加（analysis/ から上に戻る）
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import config  # ←インスタンスをimportする

class StockDataCollector:
    def __init__(self):
        self.start_date, self.end_date = self._get_last_quarter_dates()
        
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

    def collect_stock_data(self, code: str) -> Optional[pd.DataFrame]:
        """銘柄データの取得"""
        try:
            ticker = yf.Ticker(f"{code}.T")
            df = ticker.history(start=self.start_date, end=self.end_date)
            
            if df.empty:
                print(f"警告: {code}のデータが取得できませんでした")
                return None
                
            return self._calculate_indicators(df)
            
        except Exception as e:
            print(f"エラー: {code}のデータ取得失敗 - {e}")
            return None

    def _calculate_indicators(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """テクニカル指標の計算"""
        if 'Close' not in df.columns:
            print("エラー: データフレームに'Close'列が存在しません")
            return None
        df['Daily_Return'] = df['Close'].pct_change()
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['Volatility'] = df['Daily_Return'].rolling(window=20).std()
        """パフォーマンス分析"""
        if df is None or df.empty or len(df) == 0:
            return {}

        # データ長チェック
        open_value = df['Open'].iloc[0] if len(df) > 0 else None
        close_value = df['Close'].iloc[-1] if len(df) > 0 else None

        return {
            '開始日': self.start_date,
            '終了日': self.end_date,
            '始値': open_value,
            '終値': close_value,
            '最高値': df['High'].max() if len(df) > 0 else None,
            '最安値': df['Low'].min() if len(df) > 0 else None,
            '出来高平均': int(df['Volume'].mean()) if len(df) > 0 else None,
            'ボラティリティ': f"{df['Volatility'].mean():.4f}" if len(df) > 0 else None,
            '最安値': df['Low'].min(),
            '出来高平均': int(df['Volume'].mean()),
            'ボラティリティ': f"{df['Volatility'].mean():.4f}",
        }
    # 銘柄一覧の読み込み
    if not os.path.exists(config.codes_path):
        print(f"エラー: 銘柄一覧ファイルが存在しません: {config.codes_path}")
        sys.exit(1)
    try:
        codes_df = pd.read_csv(config.codes_path)
    except FileNotFoundError:
        print(f"エラー: 銘柄一覧ファイルが見つかりません: {config.codes_path}")
        sys.exit(1)
    except Exception as e:
        print(f"エラー: 銘柄一覧ファイルの読み込みに失敗しました: {e}")
        sys.exit(1)

def main():
    collector = StockDataCollector()
    results = []
    
    # 銘柄一覧の読み込み
    #./data/codes.csv
    codes_df = pd.read_csv(config.codes_path)
    
    for _, row in codes_df.iterrows():
    #    結果の保存
        output_path = os.path.join(config.output_dir, "quarterly_analysis.csv")
        os.makedirs(config.output_dir, exist_ok=True)  # ディレクトリがなければ作成
        pd.DataFrame(results).to_csv(output_path, index=False, encoding='utf-8')
        print(f"\n分析結果を保存しました: {output_path}")
        
        stock_data = collector.collect_stock_data(row['code'])
        if stock_data is None:
            continue

        analysis = dict(stock_data)
        analysis['コード'] = row['code']
        analysis['銘柄名'] = row['name'] if 'name' in row else ''
        results.append(analysis)

    
    # 結果の保存
    output_path = os.path.join(config.output_dir, "quarterly_analysis.csv")
    pd.DataFrame(results).to_csv(output_path, index=False, encoding='utf-8')
    print(f"\n分析結果を保存しました: {output_path}")

if __name__ == "__main__":
    main()
