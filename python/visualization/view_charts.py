"""
チャート表示ヘルパー
生成されたチャートを確認するためのツール
"""

import glob
import os
import sys

from python.config import config

__all__ = ["main", "print_summary", "select_csv_file", "open_charts_folder"]


def select_csv_file():
    """開発モード用のCSVファイル選択"""
    practice_dir = f"{config.data_dir}/practice"
    practice_csv_files = glob.glob(os.path.join(practice_dir, "*.csv"))

    if not practice_csv_files:
        print(f"CSVファイルが {practice_dir} に見つかりません。")
        return None

    print("\n=== 利用可能なCSVファイル ===")
    for i, file in enumerate(sorted(practice_csv_files), 1):
        filename = os.path.basename(file)
        print(f"  {i}. {filename}")

    while True:
        try:
            choice = input("\n使用するファイルの番号を入力してください: ")
            idx = int(choice) - 1
            if 0 <= idx < len(practice_csv_files):
                return practice_csv_files[idx]
            print("無効な番号です。")
        except ValueError:
            print("数字を入力してください。")


def open_charts_folder(dev_mode=False):
    """チャートフォルダを開く"""
    charts_dir = f"{config.data_dir}/chartImg"
    if dev_mode:
        selected_csv = select_csv_file()
        if not selected_csv:
            return
        charts_dir = os.path.join(
            "f{config.data_dir}/practice/charts", os.path.splitext(os.path.basename(selected_csv))[0]
        )

    abs_path = os.path.abspath(charts_dir)
    relative_path_for_display = os.path.join(os.path.basename(os.getcwd()), os.path.relpath(abs_path, os.getcwd()))

    if not os.path.exists(abs_path):
        print(f"チャートフォルダ：{relative_path_for_display}が見つかりません。")
        print("まず generate_all_charts.py を実行してください。")
        return

    print(f"\nチャート保存先: /{relative_path_for_display}")

    # List available charts
    png_files = [f for f in os.listdir(abs_path) if f.endswith(".png")]

    if not png_files:
        print("チャートファイルが見つかりません。")
        print("まず generate_all_charts.py を実行してください。")
        return

    print(f"\n利用可能なチャート: {len(png_files)}件")
    for i, file in enumerate(sorted(png_files), 1):
        if file.startswith("demo_"):
            stock_name = file.replace("demo_", "").replace(".png", "").replace("_T_", " - ")
            print(f"  {i}. {stock_name} [デモ]")
        else:
            stock_name = file.replace(".png", "").replace("_T_", " - ")
            print(f"  {i}. {stock_name}")

    if not dev_mode:
        print(f"\n詳細レポート: {relative_path_for_display}/trading_summary_portfolio_practice.txt")

    # try:
    #     subprocess.run(['open', abs_path], check=True)
    #     print(f"\nFinderでフォルダを開きました: {abs_path}")
    # except (subprocess.CalledProcessError, FileNotFoundError):
    #     print(f"\n手動でフォルダを確認してください: {abs_path}")


def print_summary(dev_mode=False):
    """トレーディングサマリーを表示"""
    if dev_mode:
        selected_csv = select_csv_file()
        if not selected_csv:
            return
        charts_dir = os.path.join(
            f"{config.data_dir}/practice/charts", os.path.splitext(os.path.basename(selected_csv))[0]
        )
    else:
        charts_dir = f"{config.data_dir}/chartImg"

    summary_file = os.path.join(charts_dir, "trading_summary_portfolio_practice.txt")

    if os.path.exists(summary_file):
        print("=== トレーディングサマリー ===")
        with open(summary_file, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.split("\n")
        preview_lines = lines[:50]

        for line in preview_lines:
            print(f"{line}\n" if line else line)

        if len(lines) > 50:
            print(f"\n... (残り {len(lines) - 50} 行)\n")
            print(f"完全版は {summary_file} を確認してください。")
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
