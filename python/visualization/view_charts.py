"""
チャート表示ヘルパー
生成されたチャートを確認するためのツール
"""

import glob
import os
import sys

__all__ = ["main", "print_summary", "select_csv_file", "open_charts_folder"]


def select_csv_file():
    """開発モード用のCSVファイル選択"""
    practice_dir = "../practice"
    csv_files = glob.glob(os.path.join(practice_dir, "*.csv"))

    if not csv_files:
        print("CSVファイルが {practice_dir} に見つかりません。")
        return None

    print("\n=== 利用可能なCSVファイル ===")
    for i, file in enumerate(sorted(csv_files), 1):
        filename = os.path.basename(file)
        print("  {i}. {filename}")

    while True:
        try:
            choice = input("\n使用するファイルの番号を入力してください: ")
            idx = int(choice) - 1
            if 0 <= idx < len(csv_files):
                return csv_files[idx]
            print("無効な番号です。")
        except ValueError:
            print("数字を入力してください。")


def open_charts_folder(dev_mode=False):
    """チャートフォルダを開く"""
    charts_dir = "../data/chartImg"
    if dev_mode:
        selected_csv = select_csv_file()
        if not selected_csv:
            return
        charts_dir = os.path.join("../practice/charts", os.path.splitext(os.path.basename(selected_csv))[0])

    abs_path = os.path.abspath(charts_dir)

    if not os.path.exists(abs_path):
        print("チャートフォルダが存在しません: {abs_path}")
        print("まず generate_all_charts.py を実行してください。")
        return

    print("\nチャート保存先: {abs_path}")

    # List available charts
    png_files = [f for f in os.listdir(abs_path) if f.endswith(".png")]

    if not png_files:
        print("チャートファイルが見つかりません。")
        print("まず generate_all_charts.py を実行してください。")
        return

    print("\n利用可能なチャート: {len(png_files)}件")
    for i, file in enumerate(sorted(png_files), 1):
        if file.startswith("demo_"):
            stock_name = file.replace("demo_", "").replace(".png", "").replace("_T_", " - ")
            print("  {i}. {stock_name} [デモ]")
        else:
            stock_name = file.replace(".png", "").replace("_T_", " - ")
            print("  {i}. {stock_name}")

    if not dev_mode:
        print("\n詳細レポート: trading_summary_portfolio_practice.txt")

    # try:
    #     subprocess.run(['open', abs_path], check=True)
    #     print("\nFinderでフォルダを開きました: {abs_path}")
    # except (subprocess.CalledProcessError, FileNotFoundError):
    #     print("\n手動でフォルダを確認してください: {abs_path}")


def print_summary(dev_mode=False):
    """トレーディングサマリーを表示"""
    if dev_mode:
        selected_csv = select_csv_file()
        if not selected_csv:
            return
        charts_dir = os.path.join("../practice/charts", os.path.splitext(os.path.basename(selected_csv))[0])
    else:
        charts_dir = "../data/chartImg"

    summary_file = os.path.join(charts_dir, "trading_summary_portfolio_practice.txt")

    if os.path.exists(summary_file):
        print("=== トレーディングサマリー ===")
        with open(summary_file, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.split("\n")
        preview_lines = lines[:50]

        for line in preview_lines:
            print(line)

        if len(lines) > 50:
            print("\n... (残り {len(lines) - 50} 行)\n")
            print("完全版は {summary_file} を確認してください。")
    else:
        print("サマリーファイルが見つかりません。")
        print("まず generate_all_charts.py を実行してください。")


def main():
    """メイン関数"""
    print("=== チャート表示ヘルパー ===")

    dev_mode = len(sys.argv) > 1 and sys.argv[1] == "dev-mode"
    if dev_mode:
        print("[開発モード] practiceフォルダ内のCSVファイルを使用します")

    if len(sys.argv) > 1 and sys.argv[-1] == "--summary":
        print_summary(dev_mode)
    else:
        open_charts_folder(dev_mode)


if __name__ == "__main__":
    main()
