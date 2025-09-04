# python/analyze.py
import sqlite3
import pandas as pd
import logging
from typing import Tuple, Optional
from ..config import config

logger = logging.getLogger(__name__)

def analyze(code: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    株価データを分析する
    
    Args:
        code: 証券コード
        
    Returns:
        Tuple[DataFrame, str]: 分析結果とシグナル
    """
    try:
        db_config = config.get_database_config()
        conn = sqlite3.connect(db_config["path"])
        
        # データ取得
        query = f"SELECT date, close FROM daily WHERE code='{code}' ORDER BY date"
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            logger.warning(f"データが見つかりません: {code}")
            return None, None
        
        # データ型変換
        df["close"] = df["close"].astype(float)
        
        # 移動平均線計算
        df["ma5"] = df["close"].rolling(config.ma_short).mean()
        df["ma25"] = df["close"].rolling(config.ma_long).mean()
        
        # データが不足している場合
        if len(df) < config.ma_long:
            logger.warning(f"データが不足しています: {code} (必要: {config.ma_long}, 実際: {len(df)})")
            return df.tail(), None
        
        # シグナル判定
        signal = _determine_signal(df)
        
        logger.info(f"分析完了: {code} - シグナル: {signal}")
        return df.tail(), signal
        
    except sqlite3.Error as e:
        logger.error(f"データベースエラー: {e}")
        return None, None
    except Exception as e:
        logger.error(f"分析エラー: {e}")
        return None, None

def _determine_signal(df: pd.DataFrame) -> Optional[str]:
    """シグナルを判定する"""
    try:
        # 最新のデータ
        current_ma5 = df["ma5"].iloc[-1]
        current_ma25 = df["ma25"].iloc[-1]
        prev_ma5 = df["ma5"].iloc[-2]
        prev_ma25 = df["ma25"].iloc[-2]
        
        # ゴールデンクロス
        if current_ma5 > current_ma25 and prev_ma5 <= prev_ma25:
            return "買いシグナル📈"
        
        # デッドクロス
        elif current_ma5 < current_ma25 and prev_ma5 >= prev_ma25:
            return "売りシグナル📉"
        
        # トレンド継続
        elif current_ma5 > current_ma25:
            return "上昇トレンド継続📈"
        else:
            return "下降トレンド継続📉"
            
    except Exception as e:
        logger.error(f"シグナル判定エラー: {e}")
        return None

if __name__ == "__main__":
    try:
        table, sig = analyze("7203.T")
        if table is not None:
            print(table)
            print("シグナル:", sig)
        else:
            print("分析に失敗しました")
    except Exception as e:
        logger.error(f"メイン処理エラー: {e}")
        print(f"エラーが発生しました: {e}")