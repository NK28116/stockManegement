"""
ローカル検証用 DB 同期スクリプト

data/my_stock_local.csv の内容を test_stock.db (SQLite) の
stocks および portfolio テーブルへ同期する。

使用方法:
    python scripts/sync_local_db.py
    python scripts/sync_local_db.py --csv data/my_stock_local.csv --db test_stock.db
"""

import argparse
import sqlite3
from pathlib import Path


_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_CSV = _ROOT / "data" / "my_stock_local.csv"
_DEFAULT_DB = _ROOT / "test_stock.db"


def _ensure_tables(conn: sqlite3.Connection) -> None:
    """stocks / portfolio テーブルを存在しなければ作成する"""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS stocks (
            code    TEXT PRIMARY KEY,
            name    TEXT,
            market  TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS portfolio (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            code                 TEXT    NOT NULL,
            name                 TEXT,
            quantity             INTEGER,
            purchase_price       REAL,
            purchase_date        TEXT    NOT NULL,
            status               TEXT,
            current_price        REAL,
            profit_loss          REAL,
            profit_loss_percent  TEXT,
            last_updated         TEXT,
            purpose              TEXT,
            UNIQUE (code, purchase_date)
        )
        """
    )
    conn.commit()


def _load_csv(csv_path: Path) -> list[dict]:
    """CSV を読み込んで辞書のリストを返す"""
    import csv

    records = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(dict(row))
    return records


def _sync(csv_path: Path, db_path: Path) -> None:
    print(f"CSV : {csv_path}")
    print(f"DB  : {db_path}")

    records = _load_csv(csv_path)
    print(f"読み込み件数: {len(records)}")

    conn = sqlite3.connect(db_path)
    _ensure_tables(conn)

    stocks_upserted = 0
    portfolio_upserted = 0

    for row in records:
        code = row.get("code", "").strip()
        name = row.get("name", "").strip()
        if not code:
            continue

        # stocks テーブル: code / name のみ登録
        conn.execute(
            """
            INSERT INTO stocks (code, name)
            VALUES (?, ?)
            ON CONFLICT(code) DO UPDATE SET name = excluded.name
            """,
            (code, name),
        )
        stocks_upserted += 1

        # portfolio テーブル: 全カラムを登録
        conn.execute(
            """
            INSERT INTO portfolio
                (code, name, quantity, purchase_price, purchase_date,
                 status, current_price, profit_loss, profit_loss_percent,
                 last_updated, purpose)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(code, purchase_date) DO UPDATE SET
                name                = excluded.name,
                quantity            = excluded.quantity,
                purchase_price      = excluded.purchase_price,
                status              = excluded.status,
                current_price       = excluded.current_price,
                profit_loss         = excluded.profit_loss,
                profit_loss_percent = excluded.profit_loss_percent,
                last_updated        = excluded.last_updated,
                purpose             = excluded.purpose
            """,
            (
                code,
                name,
                row.get("quantity"),
                row.get("purchase_price"),
                row.get("purchase_date", "").strip(),
                row.get("status", "").strip(),
                row.get("current_price"),
                row.get("profit_loss"),
                row.get("profit_loss_percent", "").strip(),
                row.get("last_updated", "").strip(),
                row.get("purpose", "").strip(),
            ),
        )
        portfolio_upserted += 1

    conn.commit()
    conn.close()

    print(f"stocks    テーブル: {stocks_upserted} 件 upsert 完了")
    print(f"portfolio テーブル: {portfolio_upserted} 件 upsert 完了")
    print("同期完了")


def main() -> None:
    parser = argparse.ArgumentParser(description="ローカルDB同期スクリプト")
    parser.add_argument("--csv", default=str(_DEFAULT_CSV), help="同期元 CSV パス")
    parser.add_argument("--db", default=str(_DEFAULT_DB), help="同期先 SQLite DB パス")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    db_path = Path(args.db)

    if not csv_path.exists():
        print(f"エラー: CSV ファイルが見つかりません: {csv_path}")
        raise SystemExit(1)

    _sync(csv_path, db_path)


if __name__ == "__main__":
    main()
