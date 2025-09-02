#!/usr/bin/env python3
"""
チャート表示ヘルパー
生成されたチャートを確認するためのツール
"""

import os
import subprocess
import sys

def open_charts_folder():
    """チャートフォルダを開く"""
    charts_dir = "../data/charts"
    abs_path = os.path.abspath(charts_dir)
    
    print(f"チャート保存先: {abs_path}")
    
    # List available charts
    png_files = [f for f in os.listdir(abs_path) if f.endswith('.png')]
    
    if not png_files:
        print("チャートファイルが見つかりません。")
        print("まず generate_all_charts.py を実行してください。")
        return
    
    print(f"\n利用可能なチャート: {len(png_files)}件")
    for i, file in enumerate(sorted(png_files), 1):
        # Extract stock info from filename
        if file.startswith('demo_'):
            stock_name = file.replace('demo_', '').replace('.png', '').replace('_T_', ' - ')
            print(f"  {i}. {stock_name} [デモ]")
        else:
            stock_name = file.replace('.png', '').replace('_T_', ' - ')
            print(f"  {i}. {stock_name}")
    
    print(f"\n詳細レポート: trading_summary_portfolio_practice.txt")
    
    # Try to open folder in Finder (macOS)
    try:
        subprocess.run(['open', abs_path], check=True)
        print(f"\nFinderでフォルダを開きました: {abs_path}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"\n手動でフォルダを確認してください: {abs_path}")

def print_summary():
    """トレーディングサマリーを表示"""
    charts_dir = "../data/charts"
    summary_file = os.path.join(charts_dir, "trading_summary_portfolio_practice.txt")
    
    if os.path.exists(summary_file):
        print("=== トレーディングサマリー ===")
        with open(summary_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Show first few stocks as preview
        lines = content.split('\n')
        preview_lines = lines[:50]  # First 50 lines
        
        for line in preview_lines:
            print(line)
        
        if len(lines) > 50:
            print(f"\n... (残り {len(lines) - 50} 行)\n")
            print(f"完全版は {summary_file} を確認してください。")
    else:
        print("サマリーファイルが見つかりません。")
        print("まず generate_all_charts.py を実行してください。")

def main():
    """メイン関数"""
    print("=== チャート表示ヘルパー ===")
    
    if len(sys.argv) > 1 and sys.argv[1] == '--summary':
        print_summary()
    else:
        open_charts_folder()

if __name__ == "__main__":
    main()
