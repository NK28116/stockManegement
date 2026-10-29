"""新しく登録した銘柄のチャートをその場で作る仕組みのテスト"""

import io
import os
import threading

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from python.trading import buy_and_sell_stock as bss
from python.trading.stock_status import StockStatus
from python.web.routes import actions
from python.web.services import chart_jobs as jobs_module
from python.web.services.chart_jobs import ChartJobs

COLUMNS = [
    "code",
    "name",
    "quantity",
    "purchase_price",
    "purchase_date",
    "purpose",
    "status",
]


# --- 待ち行列 -----------------------------------------------------------------


def test_run_generates_queued_codes_and_then_updates_signals(monkeypatch):
    calls = []
    monkeypatch.setattr(
        jobs_module, "generate_and_upload", lambda keys: calls.append(keys) or set(keys)
    )
    after = []

    jobs = ChartJobs()
    assert jobs.enqueue(["4755.T", "9984"]) == ["4755", "9984"]
    assert jobs.generating() == ["4755", "9984"]
    jobs.run(after=lambda: after.append(True))

    assert calls == [["4755", "9984"]]
    assert jobs.generating() == []
    assert jobs.failed() == []
    assert after == [True]  # シグナルの更新は 1 回だけ


def test_codes_added_while_running_are_generated_in_the_same_run(monkeypatch):
    jobs = ChartJobs()
    calls = []

    def fake_generate(keys):
        calls.append(keys)
        if len(calls) == 1:
            jobs.enqueue(["6758"])  # 作成中に次の登録が来た
            jobs.run()  # 実行中なので何もせずに戻る
        return set(keys)

    monkeypatch.setattr(jobs_module, "generate_and_upload", fake_generate)
    jobs.enqueue(["4755"])
    jobs.run()
    assert calls == [["4755"], ["6758"]]
    assert jobs.generating() == []


def test_failed_codes_are_reported_and_signals_not_updated(monkeypatch):
    monkeypatch.setattr(
        jobs_module, "generate_and_upload", lambda keys: set()
    )  # 株価が取れなかった
    after = []
    jobs = ChartJobs()
    jobs.enqueue(["4755"])
    jobs.run(after=lambda: after.append(True))
    assert jobs.failed() == ["4755"]
    assert after == []


def test_exception_does_not_leave_codes_generating(monkeypatch):
    def boom(keys):
        raise RuntimeError("matplotlib error")

    monkeypatch.setattr(jobs_module, "generate_and_upload", boom)
    jobs = ChartJobs()
    jobs.enqueue(["4755"])
    jobs.run()
    assert jobs.generating() == []
    assert jobs.failed() == ["4755"]


def test_disable_switch(monkeypatch):
    monkeypatch.setenv("DISABLE_NEW_STOCK_CHARTS", "1")
    assert not jobs_module.is_enabled()
    monkeypatch.delenv("DISABLE_NEW_STOCK_CHARTS")
    assert jobs_module.is_enabled()


# --- 作成とアップロード -----------------------------------------------------------


class _Blob:
    def __init__(self, name, uploads):
        self.name, self.uploads = name, uploads

    def upload_from_filename(self, path, content_type=None):
        self.uploads.append(self.name)

    def upload_from_string(self, data, content_type=None):
        self.uploads.append(self.name)


class _Gcs:
    use_gcs = True

    def __init__(self):
        self.uploads = []
        outer = self

        class _Bucket:
            def blob(self, name):
                return _Blob(name, outer.uploads)

        self.bucket = _Bucket()

    def get_file_content(self, path):
        return None


def test_generate_and_upload_uploads_only_the_new_stocks(monkeypatch, tmp_path):
    signals, plots = tmp_path / "chartImg", tmp_path / "plots"
    signals.mkdir()
    plots.mkdir()
    # 既にある別銘柄のチャート (アップロードしない)
    (signals / "7203_T_TOYOTA.png").write_bytes(b"x")

    class FakeVisualizer:
        def __init__(self, period, only_codes):
            assert only_codes == ["4755"]
            self.data_dir, self.plot_image_dir = str(signals), str(plots)

        def visualize_all_stocks(self, portfolio_file):
            (signals / "4755_T_RAKUTEN.png").write_bytes(b"x")
            (plots / "4755.T_RAKUTEN_indicators.png").write_bytes(b"x")

    monkeypatch.setattr(
        "python.visualization.stock_chart_visualizer.StockChartVisualizer",
        FakeVisualizer,
    )
    gcs = _Gcs()
    monkeypatch.setattr(jobs_module, "gcs", gcs)
    monkeypatch.setattr(jobs_module, "_upload_latest_indicators", lambda: None)

    assert jobs_module.generate_and_upload(["4755"]) == {"4755"}
    assert sorted(gcs.uploads) == [
        "charts/indicators/4755.T_RAKUTEN_indicators.png",
        "charts/signals/4755_T_RAKUTEN.png",
    ]


def test_visualizer_only_codes_filters_portfolio(monkeypatch):
    from python.visualization import stock_chart_visualizer as viz

    csv = "code,name\n7203.T,TOYOTA\n4755.T,RAKUTEN\n"

    class _CsvGcs:
        use_gcs = True

        def get_file_content(self, path):
            return csv.encode()

    monkeypatch.setattr(viz, "gcs", _CsvGcs())
    visualizer = viz.StockChartVisualizer(
        period="1mo", is_test_mode=True, only_codes=["4755"]
    )
    assert [s["code"] for s in visualizer.load_portfolio_stocks("my_stock.csv")] == [
        "4755.T"
    ]


# --- まとめて反映 (POST /api/actions/commit) -------------------------------------


@pytest.fixture
def client(monkeypatch):
    data = {
        "df": pd.DataFrame(
            [
                [
                    "7203.T",
                    "TOYOTA",
                    100,
                    1000.0,
                    "2026-01-01",
                    "long",
                    StockStatus.HOLDING,
                ]
            ],
            columns=COLUMNS,
        )
    }
    monkeypatch.setattr(bss, "load_codes", lambda path: data["df"].copy())
    monkeypatch.setattr(bss, "save_codes", lambda df, path: data.update(df=df))
    monkeypatch.setattr(bss, "get_price", lambda code: 1234.5)
    monkeypatch.setattr(bss, "get_name", lambda code: f"NAME-{code}")
    monkeypatch.setattr("python.utils.alert.send_alert", lambda *a, **k: None)

    generated = []
    monkeypatch.setattr(
        jobs_module,
        "generate_and_upload",
        lambda keys: generated.append(keys) or set(keys),
    )
    monkeypatch.setattr(actions, "chart_jobs", ChartJobs())

    analyzed = []

    class _Analyze:
        @staticmethod
        def main():
            analyzed.append(True)

    monkeypatch.setattr(actions, "analyze", _Analyze)
    monkeypatch.delenv("DISABLE_NEW_STOCK_CHARTS", raising=False)

    app = FastAPI()
    app.include_router(actions.router)
    data.update(generated=generated, analyzed=analyzed)
    return TestClient(app), data


def test_commit_registers_updates_and_starts_charts(client):
    http, data = client
    res = http.post(
        "/api/actions/commit",
        json={
            "registrations": [
                {"code": "4755", "quantity": 100, "purpose": "swing"},
                {"code": "9984", "quantity": 0, "status": StockStatus.WATCHING},
            ],
            "updates": [{"code": "7203", "quantity": 50}],
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["generating_charts"] == ["4755", "9984"]
    assert [item["code"] for item in body["items"]] == ["4755", "9984", "7203"]

    df = data["df"].set_index("code")
    assert df.loc["4755.T", "status"] == StockStatus.HOLDING
    assert df.loc["4755.T", "purpose"] == "swing"
    assert df.loc["9984.T", "status"] == StockStatus.WATCHING
    assert df.loc["7203.T", "quantity"] == 50

    # レスポンスのあとで、新しい銘柄だけチャートを作り、シグナルを更新する
    assert data["generated"] == [["4755", "9984"]]
    assert data["analyzed"] == [True]


def test_commit_saves_nothing_when_one_is_invalid(client):
    http, data = client
    before = data["df"].copy()
    res = http.post(
        "/api/actions/commit",
        json={
            "registrations": [
                {"code": "4755", "quantity": 100},
                {"code": "9984", "quantity": 0},
            ],
            "updates": [],
        },
    )
    assert res.status_code == 400
    assert "9984" in res.json()["detail"]
    pd.testing.assert_frame_equal(data["df"], before)
    assert data["generated"] == []


def test_commit_with_only_updates_does_not_make_charts(client):
    http, data = client
    res = http.post(
        "/api/actions/commit", json={"updates": [{"code": "7203", "quantity": 10}]}
    )
    assert res.status_code == 200, res.text
    assert res.json()["generating_charts"] == []
    assert data["generated"] == []


def test_commit_requires_changes(client):
    http, _ = client
    assert http.post("/api/actions/commit", json={}).status_code == 400


def test_status_reports_chart_generation(client, monkeypatch):
    http, _ = client
    jobs = ChartJobs()
    jobs.enqueue(["4755"])
    monkeypatch.setattr(actions, "chart_jobs", jobs)
    body = http.get("/api/actions/status").json()
    assert body["generating_charts"] == ["4755"]
    assert body["chart_failed"] == []
