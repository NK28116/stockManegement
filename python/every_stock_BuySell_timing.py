#!/usr/bin/env python3
"""
単一銘柄チャートデモ
buy/sellポイントを可視化
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from stock_chart_visualizer import StockChartVisualizer

def every_stock_BuySell_timing(ticker="7203.T", name="トヨタ自動車"):
    """単一銘柄のデモチャート作成"""
    
    print(f"=== {name} ({ticker}) チャート作成デモ ===")
    
    # Create visualizer
    visualizer = StockChartVisualizer(period="3mo")
    
    # Create stock info
    stock_info = {
        'code': ticker,
        'name': name,
        'sector': 'Demo'
    }
    
    # Fetch data
    df = visualizer.fetch_stock_data(ticker)
    if df is None:
        print("データ取得に失敗しました")
        return
    
    # Analyze with trading rules
    trades = visualizer.trading_rules.analyze_with_improved_rules(df)
    metrics = visualizer.trading_rules.calculate_performance_metrics(trades)
    
    # Create and save chart
    fig = visualizer.create_chart_with_signals(stock_info, df, trades)
    
    chart_filename = f"demo_{ticker.replace('.', '_')}_{name}.png"
    chart_path = os.path.join(visualizer.output_dir, chart_filename)
    fig.savefig(chart_path, dpi=150, bbox_inches='tight')
    
    print(f"チャート保存: {chart_path}")
    
    # Print summary
    summary = visualizer.generate_trading_summary(stock_info, trades, metrics)
    print(summary)
    
    return chart_path

if __name__ == "__main__":

    every_stock_BuySell_timing()
