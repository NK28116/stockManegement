"""
6-8月のデータ取得と分析スクリプト
動作確認兼売買練習用
"""

import yfinance as yf
import pandas as pd
import sqlite3
import logging
import os
import sys
from datetime import datetime
from typing import List, Dict

# 現在のディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import config
from portfolio_analyzer import PortfolioAnalyzer

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/data_collector.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataCollector:
    """データ収集クラス"""
    
    def __init__(self):
        self.db_config = config.get_database_config()
    
    def collect_sample_data(self, codes: List[str], start_date: str, end_date: str) -> bool:
        """
        サンプルデータを収集してデータベースに保存
        
        Args:
            codes: 証券コードのリスト
            start_date: 開始日
            end_date: 終了日
            
        Returns:
            bool: 収集が成功したかどうか
        """
        try:
            # ログディレクトリ作成
            os.makedirs('logs', exist_ok=True)
            
            conn = sqlite3.connect(self.db_config["path"])
            cur = conn.cursor()
            
            # テーブル作成
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sample_daily (
                    code TEXT,
                    date DATE,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    PRIMARY KEY (code, date)
                )
            """)
            
            success_count = 0
            
            for code in codes:
                try:
                    logger.info(f"データ収集開始: {code}")
                    ticker = yf.Ticker(code)
                    df = ticker.history(start=start_date, end=end_date)
                    
                    if not df.empty:
                        # データベースに保存
                        for date, row in df.iterrows():
                            cur.execute("""
                                INSERT OR REPLACE INTO sample_daily 
                                (code, date, open, high, low, close, volume)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                code,
                                date.strftime('%Y-%m-%d'),
                                row['Open'],
                                row['High'],
                                row['Low'],
                                row['Close'],
                                row['Volume']
                            ))
                        
                        conn.commit()
                        success_count += 1
                        logger.info(f"データ収集完了: {code} - {len(df)}件")
                    else:
                        logger.warning(f"データが取得できません: {code}")
                        
                except Exception as e:
                    logger.error(f"データ収集エラー: {code} - {e}")
            
            conn.close()
            
            logger.info(f"データ収集完了: {success_count}/{len(codes)}銘柄")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"データ収集エラー: {e}")
            return False
    
    def analyze_collected_data(self, portfolio_file: str = None) -> None:
        """収集したデータを分析"""
        analyzer = PortfolioAnalyzer()
        
        if portfolio_file:
            portfolio = analyzer.load_portfolio_from_file(portfolio_file)
        else:
            # デフォルトのサンプルポートフォリオ
            portfolio = {
                '7203.T': {'name': 'トヨタ自動車', 'quantity': 100, 'purchase_price': 2500, 'weight': 0.15},
                '6758.T': {'name': 'ソニーグループ', 'quantity': 50, 'purchase_price': 12000, 'weight': 0.12},
                '9984.T': {'name': 'ソフトバンクグループ', 'quantity': 200, 'purchase_price': 6000, 'weight': 0.20},
                '6861.T': {'name': 'キーエンス', 'quantity': 10, 'purchase_price': 50000, 'weight': 0.08},
                '7974.T': {'name': '任天堂', 'quantity': 30, 'purchase_price': 8000, 'weight': 0.10},
                '6752.T': {'name': 'パナソニック', 'quantity': 100, 'purchase_price': 1200, 'weight': 0.08},
                '8306.T': {'name': '三菱UFJフィナンシャル・グループ', 'quantity': 500, 'purchase_price': 800, 'weight': 0.12},
                '9433.T': {'name': 'KDDI', 'quantity': 100, 'purchase_price': 4000, 'weight': 0.15}
            }
        
        # 6-8月のデータを取得
        data = analyzer.fetch_historical_data(
            list(portfolio.keys()), 
            "2024-06-01", 
            "2024-08-31"
        )
        
        if data:
            returns = analyzer.calculate_returns(data)
            metrics = analyzer.calculate_portfolio_metrics(portfolio, returns)
            correlation_matrix = analyzer.calculate_correlation_matrix(returns)
            
            report = analyzer.generate_portfolio_report(portfolio, metrics, correlation_matrix)
            print(report)
            
            # 結果保存
            analyzer.save_analysis_result(report, "practice_analysis.txt")

def main():
    """メイン実行関数"""
    collector = DataCollector()
    
    # サンプル銘柄（リスク・リターンバランスが分散）
    sample_codes = [
        '7203.T',  # トヨタ（安定成長）
        '6758.T',  # ソニー（成長株）
        '9984.T',  # ソフトバンク（ハイリスク・ハイリターン）
        '6861.T',  # キーエンス（高品質成長）
        '7974.T',  # 任天堂（安定収益）
        '6752.T',  # パナソニック（バリュー）
        '8306.T',  # 三菱UFJ（金融）
        '9433.T'   # KDDI（通信）
    ]
    
    print("6-8月のデータ収集開始...")
    success = collector.collect_sample_data(sample_codes, "2024-06-01", "2024-08-31")
    
    if success:
        print("データ収集完了")
        print("分析開始...")
        collector.analyze_collected_data()
        print("分析完了")
    else:
        print("データ収集に失敗しました")

if __name__ == "__main__":
    main()
