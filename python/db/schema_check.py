# python/db/schema_check.py
"""実スキーマと Alembic 履歴の整合を検証する読み取り専用ユーティリティ (PRIDEV-487)

本モジュールは **一切 DDL を実行しない**。既存 DB を壊さずに、

    * DB に記録されている Alembic リビジョンと、スクリプト側の head の一致
    * モデル (python/db/models.py) が定義するテーブルの存在

を確認し、差分を報告する。

CLI:
    python -m python.db.schema_check          # 差分があれば終了コード 1
    python -m python.db.schema_check --json   # 機械可読な出力
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from sqlalchemy import inspect
from sqlalchemy.engine import Engine

__all__ = [
    "SchemaReport",
    "check_schema",
    "expected_tables",
    "main",
]

ALEMBIC_VERSION_TABLE = "alembic_version"


def expected_tables() -> List[str]:
    """モデルが定義する全テーブル名 (期待されるスキーマ)。"""
    from python.db.models import Base

    return sorted(Base.metadata.tables.keys())


def script_head_revisions() -> List[str]:
    """alembic/versions が示す head リビジョン。"""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    from python.config import config as app_config

    alembic_cfg = Config(str(app_config.root_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(app_config.root_dir / "alembic"))
    return sorted(ScriptDirectory.from_config(alembic_cfg).get_heads())


def db_revisions(engine: Engine) -> List[str]:
    """DB の alembic_version テーブルに記録されたリビジョン。未管理なら空。"""
    inspector = inspect(engine)
    if ALEMBIC_VERSION_TABLE not in inspector.get_table_names():
        return []
    with engine.connect() as connection:
        from sqlalchemy import text

        rows = connection.execute(text(f"SELECT version_num FROM {ALEMBIC_VERSION_TABLE}"))
        return sorted(row[0] for row in rows)


@dataclass
class SchemaReport:
    """検証結果。`ok` が False なら運用側の対応が必要。"""

    db_revisions: List[str] = field(default_factory=list)
    head_revisions: List[str] = field(default_factory=list)
    existing_tables: List[str] = field(default_factory=list)
    missing_tables: List[str] = field(default_factory=list)
    problems: List[str] = field(default_factory=list)
    hints: List[str] = field(default_factory=list)

    @property
    def revisions_match(self) -> bool:
        return self.db_revisions == self.head_revisions

    @property
    def ok(self) -> bool:
        return not self.problems

    def to_dict(self) -> Dict[str, object]:
        return {
            "ok": self.ok,
            "db_revisions": self.db_revisions,
            "head_revisions": self.head_revisions,
            "revisions_match": self.revisions_match,
            "missing_tables": self.missing_tables,
            "existing_tables": self.existing_tables,
            "problems": self.problems,
            "hints": self.hints,
        }

    def render(self) -> str:
        lines = [
            "=== DB スキーマ整合チェック (PRIDEV-487) ===",
            f"Alembic head       : {', '.join(self.head_revisions) or '(なし)'}",
            f"DB のリビジョン    : {', '.join(self.db_revisions) or '(未管理)'}",
            f"必要テーブル       : {len(self.existing_tables)}/"
            f"{len(self.existing_tables) + len(self.missing_tables)} 存在",
        ]
        if self.missing_tables:
            lines.append(f"欠落テーブル       : {', '.join(self.missing_tables)}")
        if self.problems:
            lines.append("")
            lines.extend(f"[NG] {problem}" for problem in self.problems)
            lines.extend(f"  → {hint}" for hint in self.hints)
        else:
            lines.append("")
            lines.append("[OK] 実スキーマと Alembic 履歴は整合しています")
        return "\n".join(lines)


def check_schema(engine: Optional[Engine] = None, required: Optional[Sequence[str]] = None) -> SchemaReport:
    """スキーマと Alembic 履歴の整合を検証する (読み取り専用)。"""
    if engine is None:
        from python.db.database import engine as default_engine

        engine = default_engine

    required_tables = sorted(required) if required is not None else expected_tables()
    inspector = inspect(engine)
    present = set(inspector.get_table_names())

    report = SchemaReport(
        db_revisions=db_revisions(engine),
        head_revisions=script_head_revisions(),
        existing_tables=[name for name in required_tables if name in present],
        missing_tables=[name for name in required_tables if name not in present],
    )

    if report.missing_tables:
        report.problems.append(f"必要テーブルが存在しません: {', '.join(report.missing_tables)}")
        report.hints.append("alembic upgrade head を実行してください")

    if not report.db_revisions:
        if present - {ALEMBIC_VERSION_TABLE}:
            report.problems.append("既存 DB が Alembic の管理下にありません")
            report.hints.append(
                "スキーマが最新なら alembic stamp head、そうでなければ alembic upgrade head"
            )
        else:
            report.problems.append("DB が未初期化です")
            report.hints.append("alembic upgrade head を実行してください")
    elif not report.revisions_match:
        report.problems.append(
            f"DB のリビジョン {report.db_revisions} が head {report.head_revisions} と一致しません"
        )
        report.hints.append(
            "未適用のマイグレーションがあるなら alembic upgrade head、"
            "スキーマが既に最新なら alembic stamp head"
        )

    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="実スキーマと Alembic 履歴の整合を検証する")
    parser.add_argument("--json", action="store_true", help="機械可読な JSON で出力する")
    args = parser.parse_args(argv)

    report = check_schema()
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) if args.json else report.render())
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
