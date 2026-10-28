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


def test_unknown_quantity_is_not_guessed_as_sold(tmp_path, capsys):
    """数量が欠損・非数値の旧売却ラベルは売却済みと推測しない (PRIDEV-525)。"""
    path = tmp_path / "my_stock.csv"
    _write_csv(
        path,
        [
            {"code": "1111.T", "name": "X", "quantity": "", "status": "売却（利益確定）", "purpose": "long"},
            {"code": "2222.T", "name": "Y", "quantity": "abc", "status": "売却（損切り）", "purpose": "long"},
        ],
    )

    exit_code = migrate_stock_status.main(["--csv", str(path), "--apply"])

    assert exit_code == 1
    assert "解決できないステータス" in capsys.readouterr().out
    assert _read_statuses(path) == {"1111.T": "売却（利益確定）", "2222.T": "売却（損切り）"}


def test_unresolved_value_prevents_any_partial_update(tmp_path, legacy_csv):
    """どこか 1 か所でも解決できない値があれば、他の対象も書き換えない。"""
    broken = tmp_path / "broken.csv"
    _write_csv(broken, [{"code": "1234.T", "name": "X", "quantity": "1", "status": "売却", "purpose": "long"}])
    before = legacy_csv.read_text(encoding="utf-8")

    exit_code = migrate_stock_status.main(["--csv", str(legacy_csv), "--csv", str(broken), "--apply"])

    assert exit_code == 1
    assert legacy_csv.read_text(encoding="utf-8") == before, "解決できる対象だけが移行されてはいけない"
    assert list(tmp_path.glob("*.bak-*")) == []


# --- portfolio テーブル (PRIDEV-525) -------------------------------------------
@pytest.fixture
def portfolio_engine(tmp_path):
    from datetime import date

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from python.db.models import Base, Portfolio

    engine = create_engine(f"sqlite:///{tmp_path / 'portfolio.db'}")
    Base.metadata.create_all(engine, tables=[Portfolio.__table__])
    with Session(engine) as session:
        session.add_all(
            [
                # 同じ code・異なる購入日で、数量とステータスが異なる行
                Portfolio(code="7203.T", purchase_date=date(2026, 1, 5), quantity=0, status="売却（利益確定）"),
                Portfolio(code="7203.T", purchase_date=date(2026, 3, 1), quantity=100, status="保有中"),
                Portfolio(code="7203.T", purchase_date=date(2026, 5, 1), quantity=50, status="売却（損切り）"),
                Portfolio(code="9434.T", purchase_date=date(2026, 2, 1), quantity=10, status="HOLDING"),
            ]
        )
        session.commit()
    yield engine
    engine.dispose()


def _portfolio_statuses(engine):
    from sqlalchemy import text

    with engine.connect() as connection:
        return {
            row.id: row.status
            for row in connection.execute(text("SELECT id, status FROM portfolio ORDER BY id"))
        }


def test_db_rows_with_same_code_are_migrated_independently(tmp_path, portfolio_engine):
    exit_code = migrate_stock_status.main(
        ["--csv", str(tmp_path / "absent.csv"), "--db", "--apply"], db_engine=portfolio_engine
    )

    assert exit_code == 0
    assert _portfolio_statuses(portfolio_engine) == {
        1: StockStatus.SOLD_PROFIT,
        2: StockStatus.HOLDING,
        3: StockStatus.SELL_PLANNED_LOSS,
        4: StockStatus.HOLDING,
    }


def test_db_dry_run_does_not_update(tmp_path, portfolio_engine):
    before = _portfolio_statuses(portfolio_engine)

    migrate_stock_status.main(["--csv", str(tmp_path / "absent.csv"), "--db"], db_engine=portfolio_engine)

    assert _portfolio_statuses(portfolio_engine) == before


def test_db_is_not_partially_updated_when_unresolved(tmp_path, portfolio_engine):
    from sqlalchemy import text

    with portfolio_engine.begin() as connection:
        connection.execute(text("UPDATE portfolio SET quantity = NULL WHERE id = 3"))
    before = _portfolio_statuses(portfolio_engine)

    exit_code = migrate_stock_status.main(
        ["--csv", str(tmp_path / "absent.csv"), "--db", "--apply"], db_engine=portfolio_engine
    )

    assert exit_code == 1
    assert _portfolio_statuses(portfolio_engine) == before


# --- 本番 GCS (PRIDEV-524) -----------------------------------------------------
class _FakeBlob:
    def __init__(self, bucket, name):
        self.bucket = bucket
        self.name = name

    @property
    def generation(self):
        return self.bucket.objects[self.name][1]

    def download_as_bytes(self):
        return self.bucket.objects[self.name][0]

    def upload_from_string(self, data, content_type=None, if_generation_match=None):
        current = self.bucket.objects.get(self.name)
        if if_generation_match is not None and (current is None or current[1] != if_generation_match):
            raise RuntimeError("412 Precondition Failed")
        self.bucket.write(self.name, data)


class _FakeBucket:
    """google.cloud.storage.Bucket のうち移行スクリプトが使う部分だけのスタブ。"""

    name = "test-bucket"

    def __init__(self):
        self.objects = {}
        self._generation = 0

    def write(self, name, data):
        self._generation += 1
        self.objects[name] = (data, self._generation)

    def blob(self, name):
        return _FakeBlob(self, name)

    def get_blob(self, name):
        return _FakeBlob(self, name) if name in self.objects else None

    def copy_blob(self, blob, destination_bucket, new_name, if_source_generation_match=None):
        data, generation = self.objects[blob.name]
        if if_source_generation_match is not None and generation != if_source_generation_match:
            raise RuntimeError("412 Precondition Failed")
        self.write(new_name, data)


def _csv_bytes(rows) -> bytes:
    return migrate_stock_status._to_csv(FIELDNAMES, rows).encode("utf-8")


@pytest.fixture
def gcs_bucket():
    bucket = _FakeBucket()
    bucket.write("my_stock.csv", _csv_bytes(LEGACY_ROWS))
    return bucket


def _gcs_args(tmp_path, *extra):
    return ["--csv", str(tmp_path / "absent.csv"), "--gcs", *extra]


def test_gcs_dry_run_reports_without_writing(tmp_path, gcs_bucket, capsys):
    before = dict(gcs_bucket.objects)

    exit_code = migrate_stock_status.main(_gcs_args(tmp_path), gcs_bucket=gcs_bucket)

    assert exit_code == 0
    assert gcs_bucket.objects == before
    output = capsys.readouterr().out
    assert "gs://test-bucket/my_stock.csv" in output
    assert "dry-run" in output


def test_gcs_apply_backs_up_and_migrates(tmp_path, gcs_bucket):
    original = gcs_bucket.objects["my_stock.csv"][0]

    exit_code = migrate_stock_status.main(_gcs_args(tmp_path, "--apply"), gcs_bucket=gcs_bucket)

    assert exit_code == 0
    backups = [name for name in gcs_bucket.objects if name.startswith("backups/my_stock.csv.bak-")]
    assert len(backups) == 1
    assert gcs_bucket.objects[backups[0]][0] == original, "適用前のオブジェクトを復元できること"

    migrated = gcs_bucket.objects["my_stock.csv"][0].decode("utf-8")
    statuses = {row["code"]: row["status"] for row in csv.DictReader(migrated.splitlines())}
    assert statuses["9434.T"] == StockStatus.HOLDING
    assert statuses["9193.T"] == StockStatus.SELL_PLANNED_PROFIT
    assert statuses["6503.T"] == StockStatus.SOLD_PROFIT


def test_gcs_is_untouched_when_unresolved(tmp_path, gcs_bucket):
    rows = LEGACY_ROWS + [{"code": "1234.T", "name": "X", "quantity": "1", "status": "売却", "purpose": "long"}]
    gcs_bucket.write("my_stock.csv", _csv_bytes(rows))
    before = dict(gcs_bucket.objects)

    exit_code = migrate_stock_status.main(_gcs_args(tmp_path, "--apply"), gcs_bucket=gcs_bucket)

    assert exit_code == 1
    assert gcs_bucket.objects == before, "バックアップも上書きも行わない"


def test_gcs_concurrent_update_is_not_overwritten(tmp_path, gcs_bucket):
    """読み込み後に他から更新された場合は上書きせず失敗する。"""
    source = migrate_stock_status.GcsSource(gcs_bucket, "my_stock.csv")
    rows = source.load()
    gcs_bucket.write("my_stock.csv", b"code,status\n")  # 別プロセスによる更新

    with pytest.raises(RuntimeError):
        source.write(rows, rows)
    assert gcs_bucket.objects["my_stock.csv"][0] == b"code,status\n"


def test_gcs_bucket_name_falls_back_to_env(monkeypatch):
    """--gcs-bucket が無ければ GCS_BUCKET_NAME (環境変数 / .env) を使う。"""
    from google.cloud import storage

    opened = []

    class _Client:
        def bucket(self, name):
            opened.append(name)
            return name

    monkeypatch.setattr(storage, "Client", _Client)
    monkeypatch.setenv("GCS_BUCKET_NAME", "bucket-from-env")

    assert migrate_stock_status._gcs_bucket(None) == "bucket-from-env"
    assert migrate_stock_status._gcs_bucket("explicit-bucket") == "explicit-bucket"
    assert opened == ["bucket-from-env", "explicit-bucket"]
