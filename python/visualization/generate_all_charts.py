import sys
from typing import List, Optional  # List, Optionalをインポート

"""
全銘柄チャート一括生成スクリプト
コマンドライン用の簡単版
"""

from python.visualization.stock_chart_visualizer import StockChartVisualizer

__all__ = ["main"]


def main(period: str = "3mo", codes: Optional[List[str]] = None):  # codes引数を追加
    """全銘柄のチャートを一括生成"""

    print("=== 全銘柄チャート一括生成 ===")

    # Create visualizer
    visualizer = StockChartVisualizer(period=period)

    # Generate charts for actual portfolio (my_stock.csv)
    portfolio_file = "my_stock.csv"

    print(f"対象ポートフォリオ: {portfolio_file} (実際の運用用)")
    print(f"期間: {period}")
    if codes:
        print(f"対象銘柄: {', '.join(codes)}")
        visualizer.visualize_specific_stocks(codes, portfolio_file)  # 特定銘柄のみを可視化する関数を呼び出す
    else:
        # Generate all charts
        visualizer.visualize_all_stocks(portfolio_file)

    print("\n=== チャート生成完了 ===")
    print("チャートファイルは data/chartImg フォルダに保存されました")
    print("取引サマリーレポートも同じフォルダに保存されています")


if __name__ == "__main__":
    # コマンドライン引数から期間と銘柄コードを取得
    chart_period = sys.argv[1] if len(sys.argv) > 1 else "3mo"
    chart_codes = sys.argv[2:] if len(sys.argv) > 2 else None  # 2番目以降の引数を銘柄コードとする
    main(period=chart_period, codes=chart_codes)
