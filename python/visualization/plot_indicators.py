# python/visualization/plot_indicators.py
"""
株価テクニカル指標の可視化
MACD とボリンジャーバンドをグラフ化し、画像として保存
"""

import matplotlib.pyplot as plt
import pandas as pd
from typing import Dict
import logging
import os
import sys
from pathlib import Path

# プロジェクトルートを sys.path に追加
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import Config

# ログ設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def plot_macd_bollinger(price_data: Dict[str, pd.DataFrame],
                        stock_names:Dict[str,str],
                        indicators: Dict[str, Dict[str, pd.DataFrame]],
                        save_dir: str) -> None:
    """
    銘柄ごとにMACDとボリンジャーバンドをグラフ化して保存
    """
    os.makedirs(save_dir, exist_ok=True)
    logging.info(f"保存先ディレクトリ: {save_dir}")

    for code, df in price_data.items():
        if df.empty or code not in indicators:
            continue

        macd_df = indicators[code]['MACD']
        bb_df = indicators[code]['Bollinger']

        fig, ax = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        stock_name = stock_names.get(code, "")
        
        # --- 上段: 株価 + Bollinger Band ---
        ax[0].plot(df.index, df['Close'], label='Close', color='blue')
        ax[0].plot(bb_df.index, bb_df['Upper'], label='Upper BB', linestyle='--', color='red')
        ax[0].plot(bb_df.index, bb_df['Lower'], label='Lower BB', linestyle='--', color='green')
        ax[0].plot(bb_df.index, bb_df['Middle'], label='Middle BB', linestyle='-.', color='orange')
        ax[0].set_title(f"{code}-{stock_name} の株価とボリンジャーバンド")
        ax[0].legend()
        ax[0].grid(True)

        # --- 下段: MACD ---
        ax[1].plot(macd_df.index, macd_df['MACD'], label='MACD', color='blue')
        ax[1].plot(macd_df.index, macd_df['Signal'], label='Signal', color='red')
        ax[1].bar(macd_df.index, macd_df['Histogram'], label='Histogram', color='gray', alpha=0.5)
        ax[1].set_title(f"{code}-{stock_name} のMACD")
        ax[1].legend()
        ax[1].grid(True)
        logging.info(f"グラフ作成完了: {code}")

        plt.tight_layout()
        filepath = os.path.join(save_dir, f"{code}_{stock_name}_indicators.png")
        plt.savefig(filepath)
        plt.close()
        logging.info(f"グラフ保存完了: {filepath}")