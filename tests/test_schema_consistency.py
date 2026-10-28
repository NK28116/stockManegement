"""実スキーマと Alembic 履歴の整合テスト (PRIDEV-487)

新規 DB / 既存 DB の両方を一時ファイル上に作り、破壊的操作を行わずに検証する。
"""

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from python.db import schema_check  # noqa: E402
from python.db.models import Base  # noqa: E402

REQUIRED_TABLES = ("signals", "watchlist", "stock_notes", "portfolio")


def _alembic_config(db_path: Path):
    from alembic.config import Config

    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


@pytest.fixture
def sqlite_env(tmp_path, monkeypatch):
    """env.py が参照する接続先を一時 SQLite へ向ける。"""
    db_path = tmp_path / "schema_test.db"
    monkeypatch.setenv("DB_TYPE", "sqlite")
    monkeypatch.setenv("SQLITE_PATH", str(db_path))
    return db_path


def _upgrade_head(db_path: Path) -> None:
    from alembic import command

    command.upgrade(_alembic_config(db_path), "head")


def _stamp_head(db_path: Path) -> None:
    from alembic import command

    command.stamp(_alembic_config(db_path), "head")


# --- 新規 DB -----------------------------------------------------------------
def test_migrations_apply_cleanly_to_a_new_database(sqlite_env):
    """新規 DB で migration を最後まで適用できること。"""
    _upgrade_head(sqlite_env)

    engine = create_engine(f"sqlite:///{sqlite_env}")
    tables = set(inspect(engine).get_table_names())

    for table in REQUIRED_TABLES:
        assert table in tables, f"{table} が作成されていない"
    assert set(Base.metadata.tables) <= tables, "モデル定義のテーブルに欠落がある"


def test_new_database_is_consistent_after_upgrade(sqlite_env):
    _upgrade_head(sqlite_env)
    engine = create_engine(f"sqlite:///{sqlite_env}")

    report = schema_check.check_schema(engine)

    assert report.ok, report.problems
    assert report.revisions_match
    assert report.missing_tables == []


def test_upgrade_is_idempotent(sqlite_env):
    """2 回目の upgrade が何も壊さないこと。"""
    _upgrade_head(sqlite_env)
    _upgrade_head(sqlite_env)

    engine = create_engine(f"sqlite:///{sqlite_env}")

    assert schema_check.check_schema(engine).ok


# --- 既存 DB -----------------------------------------------------------------
def test_unmanaged_existing_database_is_detected_with_stamp_hint(sqlite_env):
    """create_all で作られた既存 DB を検知し、stamp を案内すること。"""
    engine = create_engine(f"sqlite:///{sqlite_env}")
    Base.metadata.create_all(bind=engine)

    report = schema_check.check_schema(engine)

    assert report.ok is False
    assert report.missing_tables == [], "テーブル自体は揃っているはず"
    assert any("管理下にありません" in problem for problem in report.problems)
    assert any("stamp head" in hint for hint in report.hints)


def test_stamping_makes_existing_database_consistent(sqlite_env):
    engine = create_engine(f"sqlite:///{sqlite_env}")
    Base.metadata.create_all(bind=engine)

    _stamp_head(sqlite_env)

    assert schema_check.check_schema(engine).ok


def test_existing_data_is_not_recreated_or_lost(sqlite_env):
    """既存 DB に対して破壊的な再作成を行わないこと。"""
    engine = create_engine(f"sqlite:///{sqlite_env}")
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO portfolio (code, name, quantity, purchase_date) "
                "VALUES ('7203.T', 'TOYOTA', 100, '2026-01-01')"
            )
        )

    _stamp_head(sqlite_env)
    _upgrade_head(sqlite_env)

    with engine.connect() as connection:
        rows = connection.execute(text("SELECT code, name FROM portfolio")).fetchall()

    assert rows == [("7203.T", "TOYOTA")], "既存データが失われている"


def test_legacy_migration_creates_only_missing_tables(sqlite_env):
    """0003 が既存テーブルへ触らず、欠落分だけを作ること。"""
    engine = create_engine(f"sqlite:///{sqlite_env}")
    # 履歴に載っていた 3 テーブルだけを持つ「途中まで適用済み」の DB を作る
    Base.metadata.create_all(
        bind=engine,
        tables=[Base.metadata.tables[name] for name in ("signals", "watchlist", "stock_notes")],
    )
    _stamp_head(sqlite_env)
    with engine.begin() as connection:
        connection.execute(text("UPDATE alembic_version SET version_num = '0002'"))
        connection.execute(
            text("INSERT INTO watchlist (code, added_at, priority) VALUES ('9984.T', '2026-01-01', 0)")
        )

    _upgrade_head(sqlite_env)

    with engine.connect() as connection:
        watchlist = connection.execute(text("SELECT code FROM watchlist")).fetchall()
    tables = set(inspect(engine).get_table_names())

    assert watchlist == [("9984.T",)], "既存テーブルが再作成されている"
    assert "portfolio" in tables and "signal_history" in tables


# --- 欠落の検知 ---------------------------------------------------------------
def test_missing_table_is_detected(sqlite_env):
    _upgrade_head(sqlite_env)
    engine = create_engine(f"sqlite:///{sqlite_env}")
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE watchlist"))

    report = schema_check.check_schema(engine)

    assert report.ok is False
    assert "watchlist" in report.missing_tables
    assert any("upgrade head" in hint for hint in report.hints)


def test_uninitialized_database_is_reported(sqlite_env):
    engine = create_engine(f"sqlite:///{sqlite_env}")

    report = schema_check.check_schema(engine)

    assert report.ok is False
    assert any("未初期化" in problem for problem in report.problems)


# --- 読み取り専用であること ---------------------------------------------------
def test_check_schema_does_not_modify_the_database(sqlite_env):
    engine = create_engine(f"sqlite:///{sqlite_env}")

    schema_check.check_schema(engine)

    assert inspect(engine).get_table_names() == [], "検証処理がテーブルを作ってはいけない"


def test_expected_tables_come_from_models():
    assert set(schema_check.expected_tables()) == set(Base.metadata.tables)


def test_cli_exit_code_reflects_consistency(sqlite_env, monkeypatch, capsys):
    _upgrade_head(sqlite_env)
    engine = create_engine(f"sqlite:///{sqlite_env}")
    monkeypatch.setattr(schema_check, "check_schema", lambda: schema_check.SchemaReport())
    assert schema_check.main([]) == 0

    broken = schema_check.SchemaReport(problems=["欠落"], hints=["alembic upgrade head"])
    monkeypatch.setattr(schema_check, "check_schema", lambda: broken)
    assert schema_check.main([]) == 1
    assert "欠落" in capsys.readouterr().out
    engine.dispose()
