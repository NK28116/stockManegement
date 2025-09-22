"""
SQLiteデータベースを年単位でCSVにダンプし、該当データをDBから削除するスクリプト
"""

import sqlite3
from datetime import datetime
from typing import Optional

import pandas as pd

from python.config import config

# アーカイブディレクトリ作成
config.archive_dir.mkdir(parents=True, exist_ok=True)


def dump_and_delete_table_by_year(table_name: str, date_column: str, target_year: int):
    """
    指定テーブルの target_year 分をCSVにダンプし、DBから削除する
    """
    conn = sqlite3.connect(config.db_path)

    # データを読み込み
    query = """
        SELECT * FROM {table_name}
        WHERE strftime('%Y', {date_column}) = ?
    """
    df = pd.read_sql_query(query, conn, params=(str(target_year),))

    if df.empty:
        print(f"⚠ {table_name}: {target_year}年のデータはありません")
        conn.close()
        return

    # CSV出力
    output_file = config.archive_dir / "{table_name}_{target_year}.csv"
    df.to_csv(output_file, index=False, encoding="utf-8")
    print(f"✅ {table_name} {target_year}年分を保存しました: {output_file}")

    # DBから削除
    delete_query = "DELETE FROM {table_name} WHERE strftime('%Y', {date_column}) = ?"
    cur = conn.cursor()
    cur.execute(delete_query, (str(target_year),))
    conn.commit()
    conn.close()
    print(f"🗑️ {table_name} {target_year}年分をDBから削除しました")


def main(target_year: Optional[int] = None):
    """
    メイン実行関数。指定された年、または前年までのデータをダンプ＆削除する。
    """
    if target_year is None:
        # 引数が指定されない場合、自動的に前年を対象とする
        target_year = datetime.now().year - 1
        print(f"引数が指定されなかったため、自動的に前年 ({target_year}年) を対象とします。")
    elif not isinstance(target_year, int):
        print("❌ 無効な入力です。西暦の数字を入力してください。")
        return

    print(f"\n=== {target_year}年分のデータを処理開始 ===")
    dump_and_delete_table_by_year("stock_data", "date", target_year)  # テーブル名をstock_pricesからstock_dataに変更
    dump_and_delete_table_by_year("intraday", "date", target_year)  # intradayテーブルも追加
    print(f"=== {target_year}年分の処理完了 ===")


if __name__ == "__main__":
    # コマンドラインからの実行を考慮し、引数をパース
    import argparse

    parser = argparse.ArgumentParser(
        description="SQLiteデータベースを年単位でCSVにダンプし、該当データをDBから削除するスクリプト"
    )
    parser.add_argument("--year", type=int, help="ダンプ＆削除する年 (指定しない場合は前年)")
    args = parser.parse_args()
    main(args.year)
