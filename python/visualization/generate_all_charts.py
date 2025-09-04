#!/usr/bin/env python3
"""
全銘柄チャート一括生成スクリプト
コマンドライン用の簡単版
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from python.visualization.stock_chart_visualizer import StockChartVisualizer

def main():
    """全銘柄のチャートを一括生成"""
    
    print("=== 全銘柄チャート一括生成 ===")
    
    # Create visualizer
    visualizer = StockChartVisualizer(period="3mo")
    
    # Generate charts for actual portfolio (codes.csv)
    portfolio_file = "codes.csv"
    
    print(f"対象ポートフォリオ: {portfolio_file} (実際の運用用)")
    print("期間: 3ヶ月")
    
    # Generate all charts
    visualizer.visualize_all_stocks(portfolio_file)
    
    print("\n=== チャート生成完了 ===")
    print("チャートファイルは data/chartImg フォルダに保存されました")
    print("取引サマリーレポートも同じフォルダに保存されています")

if __name__ == "__main__":
    main()
