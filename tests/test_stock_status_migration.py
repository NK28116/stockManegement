"""銘柄ステータス移行スクリプトのテスト (PRIDEV-486)

一時ファイル上でのみ検証し、リポジトリのデータへは触れない。
"""

import csv
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from python.trading.stock_status import StockStatus  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "migrate_stock_status", ROOT / "scripts" / "migrate_stock_status.py"
)
migrate_stock_status = importlib.util.module_from_spec(_spec)
# dataclass の型解決に sys.modules 経由の参照が必要なため先に登録する
sys.modules["migrate_stock_status"] = migrate_stock_status
_spec.loader.exec_module(migrate_stock_status)

FIELDNAMES = ["code", "name", "quantity", "status", "purpose"]

LEGACY_ROWS = [
    {"code": "9434.T", "name": "A", "quantity": "5", "status": "保有中", "purpose": "long"},
    {"code": "7203.T", "name": "B", "quantity": "1", "status": "監視中", "purpose": "swing"},
    {"code": "9432.T", "name": "C", "quantity": "1", "status": "除外", "purpose": "long"},
    # 数量が残ったまま = 売却予定として運用されていた行
    {"code": "9193.T", "name": "D", "quantity": "1", "status": "売却（利益確定）", "purpose": "middle"},
    {"code": "5020.T", "name": "E", "quantity": "1", "status": "売却（損切り）", "purpose": "middle"},
    # 数量 0 = 実際に売却済み
    {"code": "6503.T", "name": "F", "quantity": "0", "status": "売却（利益確定）", "purpose": "middle"},
]


def _write_csv(path: Path, rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def _read_statuses(path: Path):
    with path.open(encoding="utf-8") as handle:
        return {row["code"]: row["status"] for row in csv.DictReader(handle)}


@pytest.fixture
def legacy_csv(tmp_path) -> Path:
    path = tmp_path / "my_stock.csv"
    _write_csv(path, LEGACY_ROWS)
    return path


# --- dry-run が既定 -----------------------------------------------------------
def test_dry_run_does_not_modify_the_file(legacy_csv):
    before = legacy_csv.read_text(encoding="utf-8")

    exit_code = migrate_stock_status.main(["--csv", str(legacy_csv)])

    assert exit_code == 0
    assert legacy_csv.read_text(encoding="utf-8") == before, "dry-run で書き換えてはいけない"


def test_dry_run_reports_every_change(legacy_csv, capsys):
    migrate_stock_status.main(["--csv", str(legacy_csv)])

    output = capsys.readouterr().out
    assert "変更 6 件" in output
    assert "dry-run" in output


# --- 実際の移行 ---------------------------------------------------------------
def test_apply_migrates_all_statuses(legacy_csv):
    migrate_stock_status.main(["--csv", str(legacy_csv), "--apply"])

    assert _read_statuses(legacy_csv) == {
        "9434.T": StockStatus.HOLDING,
        "7203.T": StockStatus.WATCHING,
        "9432.T": StockStatus.EXCLUDED,
        "9193.T": StockStatus.SELL_PLANNED_PROFIT,
        "5020.T": StockStatus.SELL_PLANNED_LOSS,
        "6503.T": StockStatus.SOLD_PROFIT,
    }


def test_apply_creates_a_backup(legacy_csv):
    migrate_stock_status.main(["--csv", str(legacy_csv), "--apply"])

    backups = list(legacy_csv.parent.glob("my_stock.csv.bak-*"))
    assert len(backups) == 1
    assert "保有中" in backups[0].read_text(encoding="utf-8"), "移行前の内容が残っていること"


def test_apply_is_idempotent(legacy_csv):
    migrate_stock_status.main(["--csv", str(legacy_csv), "--apply"])
    after_first = legacy_csv.read_text(encoding="utf-8")

    exit_code = migrate_stock_status.main(["--csv", str(legacy_csv), "--apply"])

    assert exit_code == 0
    assert legacy_csv.read_text(encoding="utf-8") == after_first


def test_other_columns_are_preserved(legacy_csv):
    migrate_stock_status.main(["--csv", str(legacy_csv), "--apply"])

    with legacy_csv.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert [row["purpose"] for row in rows] == [row["purpose"] for row in LEGACY_ROWS]
    assert [row["quantity"] for row in rows] == [row["quantity"] for row in LEGACY_ROWS]
    assert len(rows) == len(LEGACY_ROWS), "行が失われていない"


# --- 解決できない値 -----------------------------------------------------------
def test_unresolvable_status_is_reported_and_fails(tmp_path, capsys):
    path = tmp_path / "my_stock.csv"
    _write_csv(path, [{"code": "1234.T", "name": "X", "quantity": "1", "status": "売却", "purpose": "long"}])

    exit_code = migrate_stock_status.main(["--csv", str(path), "--apply"])

    output = capsys.readouterr().out
    assert exit_code == 1, "手動確認が必要な値が残る場合は失敗させる"
    assert "解決できないステータス" in output
    assert _read_statuses(path) == {"1234.T": "売却"}, "解決できない行は書き換えない"


def test_missing_file_is_ignored(tmp_path):
    assert migrate_stock_status.main(["--csv", str(tmp_path / "absent.csv")]) == 0
