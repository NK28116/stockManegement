#!/usr/bin/env python3
"""
全銘柄チャート一括生成スクリプト
コマンドライン用の簡単版
"""

import sys  # sysモジュールを追加

from python.visualization.stock_chart_visualizer import StockChartVisualizer

__all__ = ["main"]


def main(period="3mo", is_test_mode: bool = False):
    """全銘柄のチャートを一括生成"""

    print(
        f"=== 全銘柄チャート一括生成 (期間: {period}, テストモード: {is_test_mode}) ==="
    )

    # Create visualizer
    visualizer = StockChartVisualizer(period=period, is_test_mode=is_test_mode)

    # Generate charts for actual portfolio (my_stock.csv)
    from python.utils.gcs_client import gcs

    portfolio_file = "my_stock.csv" if gcs.use_gcs else "data/my_stock_local.csv"

    print(f"対象ポートフォリオ: {portfolio_file} (実際の運用用)")
    print(f"期間: {period}")

    # Generate all charts
    visualizer.visualize_all_stocks(portfolio_file)

    print("\n=== チャート生成完了 ===")
    print(f"チャートファイルは data/chartImg/{period} フォルダに保存されました")
    print(f"取引サマリーレポートも data/chartImg/{period} フォルダに保存されています")


if __name__ == "__main__":
    # コマンドライン引数から期間を取得
    if len(sys.argv) > 1:
        period_arg = sys.argv[1]
        if period_arg in ["1mo", "3mo", "6mo", "1y"]:
            main(period=period_arg)
        else:
            print(f"無効な期間指定です: {period_arg}。デフォルトの3moを使用します。")
            main()
    else:
        main()
