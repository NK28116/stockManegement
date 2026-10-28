#!/usr/bin/env python3
"""銘柄ステータスの保存値を英字キーへ移行する (PRIDEV-486)

旧データは status 列へ日本語の表示文字列を保存していた。
`python/trading/stock_status.py` の確定仕様に合わせて英字キーへ移行する。

「売却（利益確定）」「売却（損切り）」は、**保有数量が残っていれば売却予定**
(`SELL_PLANNED_*`)、**0 なら売却済み** (`SOLD_*`) として解決する。
sell_stock() は売却時に数量を 0 にするため、数量が残ったままの売却行は
売却予定として運用されていたものと判断できる。

既定は dry-run。実際に書き換えるには --apply を付ける。
--apply 時は対象ファイルのバックアップ (.bak-YYYYmmddHHMMSS) を作成する。

使い方:
    python scripts/migrate_stock_status.py                 # 差分の確認のみ
    python scripts/migrate_stock_status.py --apply         # CSV を移行
    python scripts/migrate_stock_status.py --apply --db    # CSV + portfolio テーブル
"""

from __future__ import annotations

import argparse
import csv
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


@dataclass
class MigrationReport:
    """移行結果。`unresolved` が残っている場合は手動対応が必要。"""

    changes: List[Dict[str, str]] = field(default_factory=list)
    unchanged: int = 0
    unresolved: List[Dict[str, str]] = field(default_factory=list)
    applied: bool = False

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
                lines.append(f"  {item['source']}: {item['code']} status={item['before']!r}")
        if not self.applied:
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
                {"source": source, "code": row.get("code", ""), "before": before}
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


def migrate_csv(path: Path, report: MigrationReport, apply: bool) -> None:
    if not path.exists():
        return
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    if "status" not in fieldnames:
        return

    migrated = migrate_rows(rows, report, source=path.name)
    if not apply or not report.changes:
        return

    backup = path.with_suffix(path.suffix + f".bak-{datetime.now():%Y%m%d%H%M%S}")
    shutil.copy2(path, backup)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(migrated)


def migrate_database(report: MigrationReport, apply: bool) -> None:
    """portfolio テーブルの status を移行する (UPDATE のみ。DROP/DELETE はしない)。"""
    from sqlalchemy import inspect, text

    from python.db.database import engine

    if "portfolio" not in inspect(engine).get_table_names():
        return

    with engine.connect() as connection:
        rows = [
            dict(row._mapping)
            for row in connection.execute(text("SELECT code, status, quantity FROM portfolio"))
        ]

    migrated = migrate_rows(rows, report, source="portfolio テーブル")
    if not apply:
        return

    with engine.begin() as connection:
        for original, updated in zip(rows, migrated):
            if original.get("status") == updated.get("status"):
                continue
            connection.execute(
                text("UPDATE portfolio SET status = :status WHERE code = :code"),
                {"status": updated["status"], "code": updated["code"]},
            )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="銘柄ステータスの保存値を英字キーへ移行する")
    parser.add_argument("--apply", action="store_true", help="実際に書き換える (既定は dry-run)")
    parser.add_argument("--db", action="store_true", help="portfolio テーブルも移行する")
    parser.add_argument("--csv", action="append", help="対象 CSV (既定: data/my_stock*.csv)")
    args = parser.parse_args(argv)

    report = MigrationReport(applied=args.apply)
    paths = [Path(item) for item in args.csv] if args.csv else list(DEFAULT_CSV_PATHS)
    for path in paths:
        migrate_csv(path, report, apply=args.apply)
    if args.db:
        migrate_database(report, apply=args.apply)

    print(report.render())
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
