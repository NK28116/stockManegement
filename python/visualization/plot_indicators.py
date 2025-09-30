# python/visualization/plot_indicators.py
"""
株価テクニカル指標の可視化
MACD とボリンジャーバンドをグラフ化し、画像として保存
"""

import logging
import os
from typing import Dict

import matplotlib
import matplotlib.pyplot as plt
import japanize_matplotlib 
import pandas as pd

from python.config import config

from dotenv import load_dotenv

load_dotenv()
# プロジェクトルートを sys.path に追加
# ログ設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Matplotlib フォント設定
matplotlib.rcParams["font.family"] = config.matplotlib_font_family  # 日本語対応（configから取得）
matplotlib.rcParams["axes.unicode_minus"] = False  # マイナス記号の文字化け対策

__all__ = ["plot_macd_bollinger"]


def plot_macd_bollinger(
    price_data: Dict[str, pd.DataFrame],
    stock_names: Dict[str, str],
    indicators: Dict[str, Dict[str, pd.DataFrame]],
    save_dir: str,
    is_test_mode: bool = False,
) -> None:
    """
    銘柄ごとにMACDとボリンジャーバンドをグラフ化して保存
    """
    if not is_test_mode:
        os.makedirs(save_dir, exist_ok=True)
        logging.info(f"保存先ディレクトリ: {save_dir}")
    else:
        logging.info("テストモードのため、グラフの保存はスキップします。")

    for code, df in price_data.items():
        if df.empty or code not in indicators:
            continue

        macd_df = indicators[code]["MACD"]
        bb_df = indicators[code]["Bollinger"]

        fig, ax = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        stock_name = stock_names.get(code, "")

        # --- 上段: 株価 + Bollinger Band ---
        ax[0].plot(df.index, df["Close"], label="Close", color="blue")
        ax[0].plot(bb_df.index, bb_df["Upper"], label="Upper BB", linestyle="--", color="red")
        ax[0].plot(bb_df.index, bb_df["Lower"], label="Lower BB", linestyle="--", color="green")
        ax[0].plot(
            bb_df.index,
            bb_df["Middle"],
            label="Middle BB",
            linestyle="-.",
            color="orange",
        )
        ax[0].set_title(f"{code}-{stock_name} の株価とボリンジャーバンド")
        ax[0].legend()
        ax[0].grid(True)

        # --- 下段: MACD ---
        ax[1].plot(macd_df.index, macd_df["MACD"], label="MACD", color="blue")
        ax[1].plot(macd_df.index, macd_df["Signal"], label="Signal", color="red")
        ax[1].bar(
            macd_df.index,
            macd_df["Histogram"],
            label="Histogram",
            color="gray",
            alpha=0.5,
        )
        ax[1].set_title(f"{code}-{stock_name} のMACD")
        ax[1].legend()
        ax[1].grid(True)
        logging.info(f"グラフ作成完了: {code}")

        plt.tight_layout()
        if not is_test_mode:
            filepath = os.path.join(save_dir, f"{code}_{stock_name}_indicators.png")
            plt.savefig(filepath)
            logging.info(f"グラフ保存完了: {filepath}")
        else:
            logging.info(f"テストモードのため、{code}のグラフ保存はスキップします。")
        plt.close()
