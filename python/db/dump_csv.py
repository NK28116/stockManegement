"""
SQLiteデータベースを年単位でCSVにダンプし、該当データをDBから削除するスクリプト
"""

import os
import sqlite3
import pandas as pd
from pathlib import Path

# プロジェクトルートを取得
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = ROOT_DIR / "python" / "db" / "stock.db"
ARCHIVE_DIR = ROOT_DIR / "data" / "archive"

# アーカイブディレクトリ作成
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

def dump_and_delete_table_by_year(table_name: str, date_column: str, target_year: int):
    """
    指定テーブルの target_year 分をCSVにダンプし、DBから削除する
    """
    conn = sqlite3.connect(DB_PATH)

    # データを読み込み
    query = f"""
        SELECT * FROM {table_name}
        WHERE strftime('%Y', {date_column}) = ?
    """
    df = pd.read_sql_query(query, conn, params=(str(target_year),))

    if df.empty:
        print(f"⚠ {table_name}: {target_year}年のデータはありません")
        conn.close()
        return

    # CSV出力
    output_file = ARCHIVE_DIR / f"{table_name}_{target_year}.csv"
    df.to_csv(output_file, index=False, encoding="utf-8")
    print(f"✅ {table_name} {target_year}年分を保存しました: {output_file}")

    # DBから削除
    delete_query = f"DELETE FROM {table_name} WHERE strftime('%Y', {date_column}) = ?"
    cur = conn.cursor()
    cur.execute(delete_query, (str(target_year),))
    conn.commit()
    conn.close()
    print(f"🗑️ {table_name} {target_year}年分をDBから削除しました")

def main():
    # ユーザーから対象年を入力
    target_year = input("ダンプ＆削除する年を入力してください (例: 2023): ").strip()
    if not target_year.isdigit():
        print("❌ 無効な入力です。西暦の数字を入力してください。")
        return
    target_year = int(target_year)

    print(f"\n=== {target_year}年分のデータを処理開始 ===")
    dump_and_delete_table_by_year("stock_prices", "date", target_year)
    dump_and_delete_table_by_year("trading_signals", "signal_date", target_year)
    print(f"=== {target_year}年分の処理完了 ===")

if __name__ == "__main__":
    main()