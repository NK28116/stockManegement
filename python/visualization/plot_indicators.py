# python/visualization/plot_indicators.py
"""
株価テクニカル指標の可視化
MACD とボリンジャーバンドをグラフ化し、画像として保存
"""

import os
import matplotlib.pyplot as plt
import pandas as pd
from typing import Dict

def plot_macd_bollinger(price_data: Dict[str, pd.DataFrame],
                        indicators: Dict[str, Dict[str, pd.DataFrame]],
                        save_dir: str = "../data/plots") -> None:
    """
    銘柄ごとにMACDとボリンジャーバンドをグラフ化して保存

    Args:
        price_data: 株価データ {銘柄コード: DataFrame}
        indicators: テクニカル指標 {銘柄コード: {'MACD': df, 'Bollinger': df}}
        save_dir: 保存先ディレクトリ
    """
    os.makedirs(save_dir, exist_ok=True)

    for code, df in price_data.items():
        if df.empty or code not in indicators:
            continue

        macd_df = indicators[code]['MACD']
        bb_df = indicators[code]['Bollinger']

        fig, ax = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        
        # --- 上段: 株価 + Bollinger Band ---
        ax[0].plot(df.index, df['Close'], label='Close', color='blue')
        ax[0].plot(bb_df.index, bb_df['Upper'], label='Upper BB', linestyle='--', color='red')
        ax[0].plot(bb_df.index, bb_df['Lower'], label='Lower BB', linestyle='--', color='green')
        ax[0].plot(bb_df.index, bb_df['Middle'], label='Middle BB', linestyle='-.', color='orange')
        ax[0].set_title(f"{code} 株価とボリンジャーバンド")
        ax[0].legend()
        ax[0].grid(True)

        # --- 下段: MACD ---
        ax[1].plot(macd_df.index, macd_df['MACD'], label='MACD', color='blue')
        ax[1].plot(macd_df.index, macd_df['Signal'], label='Signal', color='red')
        ax[1].bar(macd_df.index, macd_df['Histogram'], label='Histogram', color='gray', alpha=0.5)
        ax[1].set_title(f"{code} MACD")
        ax[1].legend()
        ax[1].grid(True)

        plt.tight_layout()
        filepath = os.path.join(save_dir, f"{code}_indicators.png")
        plt.savefig(filepath)
        plt.close()
        print(f"グラフ保存完了: {filepath}")