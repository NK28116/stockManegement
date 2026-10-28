"""GCS 同期スクリプトのテスト

保有株 CSV は GCS 上が正本。GCE の日次バッチが古い CSV で上書きしないことを確かめる。
"""

import importlib.util
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location("sync_data_to_gcs", ROOT / "scripts" / "sync_data_to_gcs.py")
sync_data_to_gcs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sync_data_to_gcs)


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x")


def test_portfolio_csv_is_never_uploaded(tmp_path, monkeypatch):
    for name in ("data/my_stock.csv", "data/my_stock_local.csv", "data/latest_indicators.json",
                 "data/plots/1mo/7203.T_TOYOTA_indicators.png", "data/chartImg/1mo/7203_T_TOYOTA.png"):
        _touch(tmp_path / name)
    monkeypatch.chdir(tmp_path)

    remote_paths = [remote for _, remote in sync_data_to_gcs.build_sync_list("1mo")]

    assert not any("my_stock" in remote for remote in remote_paths), "保有株 CSV を GCS へ送ってはいけない"
    assert remote_paths == [
        "latest_indicators.json",
        "charts/indicators/7203.T_TOYOTA_indicators.png",
        "charts/signals/7203_T_TOYOTA.png",
    ]


def test_only_the_requested_period_is_synced(tmp_path, monkeypatch):
    _touch(tmp_path / "data/plots/3mo/a.png")
    _touch(tmp_path / "data/chartImg/1mo/b.png")
    monkeypatch.chdir(tmp_path)

    remote_paths = [remote for _, remote in sync_data_to_gcs.build_sync_list("1mo")]

    assert "charts/signals/b.png" in remote_paths
    assert not any(path.endswith("a.png") for path in remote_paths)
    assert os.getcwd() == str(tmp_path)
