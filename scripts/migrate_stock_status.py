#!/usr/bin/env python3
"""銘柄ステータスの保存値を英字キーへ移行する (PRIDEV-486)

旧データは status 列へ日本語の表示文字列を保存していた。
`python/trading/stock_status.py` の確定仕様に合わせて英字キーへ移行する。

「売却（利益確定）」「売却（損切り）」は、**保有数量が残っていれば売却予定**
(`SELL_PLANNED_*`)、**0 なら売却済み** (`SOLD_*`) として解決する。
sell_stock() は売却時に数量を 0 にするため、数量が残ったままの売却行は
売却予定として運用されていたものと判断できる。

数量が欠損・非数値の旧売却ラベルは推測せず「解決できない値」として報告する。
解決できない値が 1 件でもあれば、--apply でも **どの対象も書き換えない**。

既定は dry-run。実際に書き換えるには --apply を付ける。
--apply 時は対象ファイルのバックアップ (.bak-YYYYmmddHHMMSS) を作成する。
GCS は `backups/` 配下へ元オブジェクトをコピーしてから上書きする。

使い方:
    python scripts/migrate_stock_status.py                 # 差分の確認のみ
    python scripts/migrate_stock_status.py --apply         # CSV を移行
    python scripts/migrate_stock_status.py --apply --db    # CSV + portfolio テーブル
    python scripts/migrate_stock_status.py --gcs           # 本番 GCS の差分確認
    python scripts/migrate_stock_status.py --apply --gcs --db  # CSV + GCS + DB
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from python.trading.stock_status import normalize, status_keys  # noqa: E402

DEFAULT_CSV_PATHS = (
    ROOT / "data" / "my_stock.csv",
    ROOT / "data" / "my_stock_local.csv",
)
# 本番 (GCS_BUCKET_NAME 設定時) にチャート一覧が読む CSV
DEFAULT_GCS_OBJECT = "my_stock.csv"


@dataclass
class MigrationReport:
    """移行結果。`unresolved` が残っている場合は手動対応が必要。"""

    changes: List[Dict[str, str]] = field(default_factory=list)
    unchanged: int = 0
    unresolved: List[Dict[str, str]] = field(default_factory=list)
    applied: bool = False
    aborted: bool = False

    @property
    def ok(self) -> bool:
        return not self.unresolved

    def render(self) -> str:
        lines = [f"変更 {len(self.changes)} 件 / 変更なし {self.unchanged} 件"]
        for change in self.changes:
            lines.append(
                f"  {change['source']}: {change['code']} "
                f"{change['before']!r} -> {change['after']!r} (quantity={change['quantity']})"
            )
        if self.unresolved:
            lines.append("")
            lines.append("[NG] 解決できないステータスがあります (手動で確認してください):")
            for item in self.unresolved:
                lines.append(
                    f"  {item['source']}: {item['code']} status={item['before']!r}"
                    f" (quantity={item.get('quantity')!r})"
                )
        if self.aborted:
            lines.append("")
            lines.append("解決できない値があるため、どの対象も書き換えずに中止しました。")
        elif not self.applied:
            lines.append("")
            lines.append("dry-run です。実際に書き換えるには --apply を付けてください。")
        return "\n".join(lines)


def migrate_rows(
    rows: Sequence[Dict[str, str]], report: MigrationReport, source: str
) -> List[Dict[str, str]]:
    """行の status を英字キーへ正規化する (純粋関数。副作用なし)。"""
    migrated: List[Dict[str, str]] = []
    known = set(status_keys())
    for row in rows:
        updated = dict(row)
        before = (row.get("status") or "").strip()
        quantity = row.get("quantity")
        after = normalize(before, quantity)

        if not before:
            report.unchanged += 1
        elif after is None:
            report.unresolved.append(
                {
                    "source": source,
                    "code": row.get("code", ""),
                    "before": before,
                    "quantity": quantity,
                }
            )
        elif after == before and before in known:
            report.unchanged += 1
        else:
            updated["status"] = after
            report.changes.append(
                {
                    "source": source,
                    "code": row.get("code", ""),
                    "before": before,
                    "after": after,
                    "quantity": str(quantity),
                }
            )
        migrated.append(updated)
    return migrated


class CsvSource:
    """ローカル CSV ファイル。"""

    def __init__(self, path: Path):
        self.path = path
        self.name = path.name
        self.fieldnames: List[str] = []

    def load(self) -> Optional[List[Dict[str, str]]]:
        if not self.path.exists():
            return None
        with self.path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            self.fieldnames = list(reader.fieldnames or [])
            rows = list(reader)
        return rows if "status" in self.fieldnames else None

    def write(self, rows: List[Dict[str, str]], migrated: List[Dict[str, str]]) -> None:
        backup = self.path.with_suffix(self.path.suffix + f".bak-{_timestamp()}")
        shutil.copy2(self.path, backup)
        with self.path.open("w", encoding="utf-8", newline="") as handle:
            handle.write(_to_csv(self.fieldnames, migrated))


class GcsSource:
    """本番画面が参照する GCS 上の CSV (PRIDEV-524)。

    適用時は元オブジェクトを `backups/<名前>.bak-YYYYmmddHHMMSS` へコピーしてから、
    読み込んだ時点の generation を条件に上書きする。移行中に他から更新されていれば
    上書きせずに失敗する (後勝ちで更新を失わないため)。
    """

    def __init__(self, bucket, object_name: str):
        self.bucket = bucket
        self.object_name = object_name
        self.name = f"gs://{getattr(bucket, 'name', '?')}/{object_name}"
        self.fieldnames: List[str] = []
        self._generation = None
        self.backup_name: Optional[str] = None

    def load(self) -> Optional[List[Dict[str, str]]]:
        blob = self.bucket.get_blob(self.object_name)
        if blob is None:
            return None
        self._generation = blob.generation
        reader = csv.DictReader(io.StringIO(blob.download_as_bytes().decode("utf-8")))
        self.fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
        return rows if "status" in self.fieldnames else None

    def write(self, rows: List[Dict[str, str]], migrated: List[Dict[str, str]]) -> None:
        source_blob = self.bucket.blob(self.object_name)
        self.backup_name = f"backups/{self.object_name}.bak-{_timestamp()}"
        self.bucket.copy_blob(
            source_blob,
            self.bucket,
            self.backup_name,
            if_source_generation_match=self._generation,
        )
        self.bucket.blob(self.object_name).upload_from_string(
            _to_csv(self.fieldnames, migrated).encode("utf-8"),
            content_type="text/csv",
            if_generation_match=self._generation,
        )


class DatabaseSource:
    """portfolio テーブル。主キー id 単位で UPDATE する (PRIDEV-525)。

    portfolio は code + purchase_date で一意のため、同じ code の行が複数存在し得る。
    code で更新すると各行の変換結果が混線するので、必ず id で 1 行ずつ更新する。
    """

    name = "portfolio テーブル"

    def __init__(self, engine):
        self.engine = engine

    def load(self) -> Optional[List[Dict[str, str]]]:
        from sqlalchemy import inspect, text

        if "portfolio" not in inspect(self.engine).get_table_names():
            return None
        with self.engine.connect() as connection:
            return [
                dict(row._mapping)
                for row in connection.execute(
                    text("SELECT id, code, status, quantity FROM portfolio ORDER BY id")
                )
            ]

    def write(self, rows: List[Dict[str, str]], migrated: List[Dict[str, str]]) -> None:
        from sqlalchemy import text

        # 1 トランザクションで適用し、途中で失敗したら全体をロールバックする
        with self.engine.begin() as connection:
            for original, updated in zip(rows, migrated):
                if original.get("status") == updated.get("status"):
                    continue
                result = connection.execute(
                    text("UPDATE portfolio SET status = :status WHERE id = :id"),
                    {"status": updated["status"], "id": original["id"]},
                )
                if result.rowcount != 1:
                    raise RuntimeError(f"portfolio id={original['id']} を一意に更新できませんでした")


def _timestamp() -> str:
    return f"{datetime.now():%Y%m%d%H%M%S}"


def _to_csv(fieldnames: Sequence[str], rows: Sequence[Dict[str, str]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(fieldnames))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def run_migration(sources: Sequence[object], report: MigrationReport, apply: bool) -> None:
    """全ソースを読み込んで差分を確定してから書き込む。

    解決できない値が 1 件でもあれば、どのソースも書き換えない
    (CSV / GCS / DB の一部だけが移行された中途半端な状態を作らない / PRIDEV-525)。
    """
    loaded = []
    for source in sources:
        rows = source.load()
        if rows is None:
            continue
        changes_before = len(report.changes)
        migrated = migrate_rows(rows, report, source=source.name)
        if len(report.changes) > changes_before:
            loaded.append((source, rows, migrated))

    if not apply:
        return
    if report.unresolved:
        report.applied = False
        report.aborted = True
        return
    for source, rows, migrated in loaded:
        source.write(rows, migrated)


def _gcs_bucket(bucket_name: Optional[str]):
    from google.cloud import storage

    name = bucket_name or os.getenv("GCS_BUCKET_NAME")
    if not name:
        raise SystemExit("--gcs には GCS_BUCKET_NAME または --gcs-bucket の指定が必要です")
    return storage.Client().bucket(name)


def main(argv: Optional[Sequence[str]] = None, *, gcs_bucket=None, db_engine=None) -> int:
    parser = argparse.ArgumentParser(description="銘柄ステータスの保存値を英字キーへ移行する")
    parser.add_argument("--apply", action="store_true", help="実際に書き換える (既定は dry-run)")
    parser.add_argument("--db", action="store_true", help="portfolio テーブルも移行する")
    parser.add_argument("--csv", action="append", help="対象 CSV (既定: data/my_stock*.csv)")
    parser.add_argument(
        "--gcs", action="store_true", help="本番画面が参照する GCS 上の CSV も移行する"
    )
    parser.add_argument("--gcs-bucket", help="対象バケット (既定: 環境変数 GCS_BUCKET_NAME)")
    parser.add_argument(
        "--gcs-object", default=DEFAULT_GCS_OBJECT, help=f"対象オブジェクト (既定: {DEFAULT_GCS_OBJECT})"
    )
    args = parser.parse_args(argv)

    report = MigrationReport(applied=args.apply)
    paths = [Path(item) for item in args.csv] if args.csv else list(DEFAULT_CSV_PATHS)
    sources: List[object] = [CsvSource(path) for path in paths]
    if args.gcs:
        bucket = gcs_bucket if gcs_bucket is not None else _gcs_bucket(args.gcs_bucket)
        sources.append(GcsSource(bucket, args.gcs_object))
    if args.db:
        if db_engine is None:
            from python.db.database import engine as db_engine
        sources.append(DatabaseSource(db_engine))

    run_migration(sources, report, apply=args.apply)

    print(report.render())
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
