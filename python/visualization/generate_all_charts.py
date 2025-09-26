#!/usr/bin/env python3
"""
全銘柄チャート一括生成スクリプト
コマンドライン用の簡単版
"""

from python.visualization.stock_chart_visualizer import StockChartVisualizer

__all__ = ["main"]


def main(period="3mo", is_test_mode: bool = False):
    """全銘柄のチャートを一括生成"""

    print(f"=== 全銘柄チャート一括生成 (テストモード: {is_test_mode}) ===")

    # Create visualizer
    visualizer = StockChartVisualizer(period=period, is_test_mode=is_test_mode)

    # Generate charts for actual portfolio (my_stock.csv)
    portfolio_file = "my_stock.csv"

    print(f"対象ポートフォリオ: {portfolio_file} (実際の運用用)")
    print(f"期間: {period}")

    # Generate all charts
    visualizer.visualize_all_stocks(portfolio_file)

    print("\n=== チャート生成完了 ===")
    print("チャートファイルは data/chartImg フォルダに保存されました")
    print("取引サマリーレポートも同じフォルダに保存されています")


if __name__ == "__main__":
    main()
