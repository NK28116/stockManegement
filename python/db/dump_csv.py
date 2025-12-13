"""
PostgreSQLデータベースを年単位でCSVにダンプし、該当データをDBから削除するスクリプト
"""

from datetime import datetime
from typing import Optional

import pandas as pd
import psycopg2
from psycopg2 import Error as PgError

from python.config import config

# アーカイブディレクトリ作成
config.archive_dir.mkdir(parents=True, exist_ok=True)


def dump_and_delete_table_by_year(table_name: str, date_column: str, target_year: int):
    """
    指定テーブルの target_year 分をCSVにダンプし、DBから削除する
    """
    conn = None
    try:
        db_config = config.get_db_config()
        conn = psycopg2.connect(**db_config)

        # データを読み込み
        query = f"""
            SELECT * FROM {table_name}
            WHERE EXTRACT(YEAR FROM {date_column}) = %s
        """
        df = pd.read_sql_query(query, conn, params=(str(target_year),))

        if df.empty:
            print(f"⚠ {table_name}: {target_year}年のデータはありません")
            return

        # CSV出力
        output_file = config.archive_dir / f"{table_name}_{target_year}.csv"
        df.to_csv(output_file, index=False, encoding="utf-8")
        print(f"✅ {table_name} {target_year}年分を保存しました: {output_file}")

        # DBから削除
        delete_query = (
            f"DELETE FROM {table_name} WHERE EXTRACT(YEAR FROM {date_column}) = %s"
        )
        cur = conn.cursor()
        cur.execute(delete_query, (str(target_year),))
        conn.commit()
        print(f"🗑️ {table_name} {target_year}年分をDBから削除しました")

    except PgError as e:
        print(f"❌ データベース操作エラー: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def main(target_year: Optional[int] = None):
    """
    メイン実行関数。指定された年、または前年までのデータをダンプ＆削除する。
    """
    if target_year is None:
        # 引数が指定されない場合、自動的に前年を対象とする
        target_year = datetime.now().year - 1
        print(
            f"引数が指定されなかったため、自動的に前年 ({target_year}年) を対象とします。"
        )
    elif not isinstance(target_year, int):
        print("❌ 無効な入力です。西暦の数字を入力してください。")
        return

    print(f"\n=== {target_year}年分のデータを処理開始 ===")
    dump_and_delete_table_by_year("stock_data", "date", target_year)
    dump_and_delete_table_by_year(
        "intraday", "timestamp", target_year
    )  # intradayテーブルのdate_columnをtimestampに変更
    print(f"=== {target_year}年分の処理完了 ===")


if __name__ == "__main__":
    # コマンドラインからの実行を考慮し、引数をパース
    import argparse

    parser = argparse.ArgumentParser(
        description="PostgreSQLデータベースを年単位でCSVにダンプし、該当データをDBから削除するスクリプト"
    )
    parser.add_argument(
        "--year", type=int, help="ダンプ＆削除する年 (指定しない場合は前年)"
    )
    args = parser.parse_args()
    main(args.year)
