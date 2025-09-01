"""
監視機能モジュール
分足・日足での株価監視とアラート機能
"""

import yfinance as yf
import sqlite3
import pandas as pd
import logging
import time
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# 現在のディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import config

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/watch.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class StockWatcher:
    """株価監視クラス"""
    
    def __init__(self):
        self.db_config = config.get_database_config()
        self.alert_thresholds = {
            "crash_threshold": -5.0,  # 5%以上の急落でアラート
            "volatility_threshold": 3.0,  # 3%以上の変動でアラート
            "volume_spike": 2.0,  # 出来高が2倍以上でアラート
        }
    
    def watch_intraday(self, codes: List[str], interval: int = 60) -> None:
        """
        分足で監視して暴落に備える
        
        Args:
            codes: 監視する証券コードのリスト
            interval: 監視間隔（秒）
        """
        logger.info(f"分足監視開始: {codes}")
        
        while True:
            try:
                for code in codes:
                    self._check_intraday_crash(code)
                
                # データベースに保存
                self._save_intraday_data(codes)
                
                logger.info(f"分足監視完了: {datetime.now().strftime('%H:%M:%S')}")
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("分足監視を停止しました")
                break
            except Exception as e:
                logger.error(f"分足監視エラー: {e}")
                time.sleep(interval)
    
    def watch_daily(self, codes: List[str]) -> Dict[str, str]:
        """
        日足で監視して売買ルールに基づいた評価をする
        
        Args:
            codes: 監視する証券コードのリスト
            
        Returns:
            Dict[str, str]: 銘柄コードと評価結果
        """
        logger.info(f"日足監視開始: {codes}")
        evaluations = {}
        
        try:
            for code in codes:
                evaluation = self._evaluate_daily_trading(code)
                evaluations[code] = evaluation
                
                # 重要なシグナルの場合はログ出力
                if "売り" in evaluation or "買い" in evaluation:
                    logger.warning(f"重要シグナル: {code} - {evaluation}")
            
            logger.info(f"日足監視完了: {len(evaluations)}銘柄")
            return evaluations
            
        except Exception as e:
            logger.error(f"日足監視エラー: {e}")
            return {}
    
    def _check_intraday_crash(self, code: str) -> None:
        """分足での暴落チェック"""
        try:
            # 最新の株価データを取得
            ticker = yf.Ticker(code)
            current_data = ticker.history(period="1d", interval="1m")
            
            if current_data.empty:
                logger.warning(f"データが取得できません: {code}")
                return
            
            # 最新価格と前回価格を比較
            current_price = current_data['Close'].iloc[-1]
            prev_price = current_data['Close'].iloc[-2] if len(current_data) > 1 else current_price
            
            # 価格変動率を計算
            price_change_percent = ((current_price - prev_price) / prev_price) * 100
            
            # 暴落判定
            if price_change_percent <= self.alert_thresholds["crash_threshold"]:
                self._trigger_crash_alert(code, current_price, price_change_percent)
            
            # ボラティリティチェック
            if abs(price_change_percent) >= self.alert_thresholds["volatility_threshold"]:
                self._trigger_volatility_alert(code, current_price, price_change_percent)
            
            # 出来高スパイクチェック
            current_volume = current_data['Volume'].iloc[-1]
            avg_volume = current_data['Volume'].rolling(5).mean().iloc[-1]
            
            if avg_volume > 0 and current_volume >= avg_volume * self.alert_thresholds["volume_spike"]:
                self._trigger_volume_alert(code, current_volume, avg_volume)
                
        except Exception as e:
            logger.error(f"暴落チェックエラー: {code} - {e}")
    
    def _evaluate_daily_trading(self, code: str) -> str:
        """日足での売買ルール評価"""
        try:
            # 日足データを取得
            ticker = yf.Ticker(code)
            df = ticker.history(period="1mo")
            
            if df.empty or len(df) < 25:
                return "データ不足"
            
            # 移動平均線計算
            df['MA5'] = df['Close'].rolling(5).mean()
            df['MA25'] = df['Close'].rolling(25).mean()
            
            # 最新データ
            current_price = df['Close'].iloc[-1]
            current_ma5 = df['MA5'].iloc[-1]
            current_ma25 = df['MA25'].iloc[-1]
            prev_ma5 = df['MA5'].iloc[-2]
            prev_ma25 = df['MA25'].iloc[-2]
            
            # RSI計算
            rsi = self._calculate_rsi(df['Close'])
            current_rsi = rsi.iloc[-1] if not rsi.empty else 50
            
            # 評価ロジック
            evaluation = []
            
            # 移動平均線クロス
            if current_ma5 > current_ma25 and prev_ma5 <= prev_ma25:
                evaluation.append("ゴールデンクロス（買いシグナル）")
            elif current_ma5 < current_ma25 and prev_ma5 >= prev_ma25:
                evaluation.append("デッドクロス（売りシグナル）")
            
            # RSI判定
            if current_rsi >= 70:
                evaluation.append("RSI過買い（売り検討）")
            elif current_rsi <= 30:
                evaluation.append("RSI過売り（買い検討）")
            
            # トレンド判定
            if current_ma5 > current_ma25:
                evaluation.append("上昇トレンド")
            else:
                evaluation.append("下降トレンド")
            
            # 価格位置
            if current_price > current_ma25 * 1.1:
                evaluation.append("高値圏")
            elif current_price < current_ma25 * 0.9:
                evaluation.append("安値圏")
            
            return " | ".join(evaluation) if evaluation else "中立"
            
        except Exception as e:
            logger.error(f"日足評価エラー: {code} - {e}")
            return "エラー"
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """RSIを計算"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except Exception as e:
            logger.error(f"RSI計算エラー: {e}")
            return pd.Series()
    
    def _trigger_crash_alert(self, code: str, price: float, change_percent: float) -> None:
        """暴落アラート"""
        message = f"🚨 暴落アラート: {code} - 価格: {price:.2f}円, 変動: {change_percent:.2f}%"
        logger.critical(message)
        print(f"\n{message}\n")
    
    def _trigger_volatility_alert(self, code: str, price: float, change_percent: float) -> None:
        """ボラティリティアラート"""
        message = f"⚠️ 高ボラティリティ: {code} - 価格: {price:.2f}円, 変動: {change_percent:.2f}%"
        logger.warning(message)
        print(f"\n{message}\n")
    
    def _trigger_volume_alert(self, code: str, volume: int, avg_volume: float) -> None:
        """出来高アラート"""
        message = f"📊 出来高急増: {code} - 出来高: {volume:,}, 平均: {avg_volume:.0f}"
        logger.info(message)
        print(f"\n{message}\n")
    
    def _save_intraday_data(self, codes: List[str]) -> None:
        """分足データをデータベースに保存"""
        try:
            conn = sqlite3.connect(self.db_config["path"])
            cur = conn.cursor()
            
            # テーブル作成
            cur.execute("""
                CREATE TABLE IF NOT EXISTS intraday (
                    code TEXT,
                    timestamp DATETIME,
                    price REAL,
                    volume INTEGER,
                    PRIMARY KEY (code, timestamp)
                )
            """)
            
            for code in codes:
                ticker = yf.Ticker(code)
                data = ticker.history(period="1d", interval="1m")
                
                if not data.empty:
                    latest = data.iloc[-1]
                    timestamp = data.index[-1].strftime("%Y-%m-%d %H:%M:%S")
                    
                    cur.execute("""
                        INSERT OR REPLACE INTO intraday (code, timestamp, price, volume)
                        VALUES (?, ?, ?, ?)
                    """, (code, timestamp, latest['Close'], latest['Volume']))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"データ保存エラー: {e}")

def watch_stocks(codes: List[str], mode: str = "daily") -> None:
    """
    株価監視のメイン関数
    
    Args:
        codes: 監視する証券コードのリスト
        mode: 監視モード ("intraday" または "daily")
    """
    watcher = StockWatcher()
    
    if mode == "intraday":
        print(f"分足監視開始: {codes}")
        print("Ctrl+Cで停止")
        watcher.watch_intraday(codes)
    else:
        print(f"日足監視開始: {codes}")
        evaluations = watcher.watch_daily(codes)
        
        print("\n=== 評価結果 ===")
        for code, evaluation in evaluations.items():
            print(f"{code}: {evaluation}")

if __name__ == "__main__":
    # 監視する銘柄リスト（例）
    watch_codes = ["7203.T", "6758.T", "9984.T"]  # トヨタ、ソニー、ソフトバンク
    
    # 日足監視（推奨）
    watch_stocks(watch_codes, "daily")
    
    # 分足監視（長時間実行）
    # watch_stocks(watch_codes, "intraday")
