"""ダッシュボードからの銘柄登録 (購入 / 次回のスイングで購入 / 監視中) のテスト

- 区分を選んで登録でき、保有中の行は予定の行で上書きしない
- 予定・監視の銘柄を購入したときは、新しい購入として記録し直す
- 登録したばかりでチャートの無い銘柄も一覧に出る (分析待ち)
"""

import asyncio

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from python.trading import buy_and_sell_stock as bss
from python.trading.stock_status import StockStatus
from python.web.routes import actions, charts

COLUMNS = ["code", "name", "quantity", "purchase_price", "purchase_date", "purpose", "status"]


def _df(*rows):
    return pd.DataFrame(list(rows), columns=COLUMNS)


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    """株価・銘柄名の取得と通知を外部へ出さない"""
    monkeypatch.setattr(bss, "get_price", lambda code: 1234.5)
    monkeypatch.setattr(bss, "get_name", lambda code: f"NAME-{code}")
    monkeypatch.setattr("python.utils.alert.send_alert", lambda *a, **k: None)


# --- 銘柄コード ---------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [("7203", "7203.T"), (" 7203 ", "7203.T"), ("285a", "285A.T"), ("7203.T", "7203.T"), ("AAPL", "AAPL")],
)
def test_normalize_code(raw, expected):
    assert bss.normalize_code(raw) == expected


# --- 次回のスイングで購入 / 監視中 -------------------------------------------


@pytest.mark.parametrize("status", [StockStatus.NEXT_BUY, StockStatus.WATCHING])
def test_register_planned_adds_new_row(status):
    df = bss.register_planned(_df(), "7203.T", status, 0, None, "swing")

    row = df.iloc[0]
    assert row["code"] == "7203.T"
    assert row["status"] == status
    assert row["quantity"] == 0
    assert row["purchase_price"] == 1234.5  # 価格を省略したら現在値を参考価格として記録
    assert row["purpose"] == "swing"


def test_register_planned_updates_watching_row():
    df = _df(["7203.T", "T", 0, 1000.0, "2026-01-01", "", StockStatus.WATCHING])
    df = bss.register_planned(df, "7203.T", StockStatus.NEXT_BUY, 100, 2000.0)

    assert len(df) == 1
    assert df.iloc[0]["status"] == StockStatus.NEXT_BUY
    assert df.iloc[0]["quantity"] == 100
    assert df.iloc[0]["purchase_price"] == 2000.0


def test_register_planned_refuses_held_row():
    df = _df(["7203.T", "T", 100, 1000.0, "2026-01-01", "", StockStatus.HOLDING])
    with pytest.raises(ValueError):
        bss.register_planned(df, "7203.T", StockStatus.WATCHING)


def test_register_planned_rejects_other_status():
    with pytest.raises(ValueError):
        bss.register_planned(_df(), "7203.T", StockStatus.HOLDING)


# --- 購入 -------------------------------------------------------------------


def test_buy_planned_row_records_new_purchase():
    df = _df(["7203.T", "T", 100, 1000.0, "2026-01-01", "swing", StockStatus.NEXT_BUY])
    df = bss.buy(df, "7203.T", 50, 2000.0)

    row = df.iloc[0]
    assert row["status"] == StockStatus.HOLDING
    # 予定の 100 株・参考価格と合算しない
    assert row["quantity"] == 50
    assert row["purchase_price"] == 2000.0
    assert row["purchase_date"] != "2026-01-01"


def test_buy_held_row_averages_price():
    df = _df(["7203.T", "T", 100, 1000.0, "2026-01-01", "", StockStatus.HOLDING])
    df = bss.buy(df, "7203.T", 100, 2000.0)

    assert df.iloc[0]["quantity"] == 200
    assert df.iloc[0]["purchase_price"] == 1500.0
    assert df.iloc[0]["purchase_date"] == "2026-01-01"


def test_buy_blank_status_row_is_treated_as_held():
    """ステータスが空欄の行は保有中とみなし、記録をリセットしない"""
    df = _df(["7203.T", "T", 100, 1000.0, "2026-01-01", "", ""])
    df = bss.buy(df, "7203.T", 100, 2000.0)
    assert df.iloc[0]["quantity"] == 200


def test_buy_without_price_uses_current_price():
    df = bss.buy(_df(), "7203.T", 10, 0)
    assert df.iloc[0]["purchase_price"] == 1234.5


def test_refresh_prices_keeps_planned_rows_without_quantity():
    df = _df(
        ["7203.T", "T", 0, 1000.0, "2026-01-01", "", StockStatus.WATCHING],
        ["6758.T", "S", 0, 1000.0, "2026-01-01", "", StockStatus.NEXT_BUY],
        ["9984.T", "B", 0, 1000.0, "2026-01-01", "", StockStatus.HOLDING],
    )
    kept = bss.refresh_prices(df)
    assert sorted(kept["code"]) == ["6758.T", "7203.T"]


# --- API --------------------------------------------------------------------


@pytest.fixture
def api(monkeypatch):
    store = {"df": _df(["9984.T", "B", 100, 1000.0, "2026-01-01", "", StockStatus.HOLDING])}
    monkeypatch.setattr(bss, "load_codes", lambda path: store["df"].copy())
    monkeypatch.setattr(bss, "save_codes", lambda df, path: store.update(df=df))
    app = FastAPI()
    app.include_router(actions.router)
    return TestClient(app), store


@pytest.mark.parametrize("status", [StockStatus.NEXT_BUY, StockStatus.WATCHING])
def test_api_registers_planned_stock(api, status):
    client, store = api
    res = client.post("/api/actions/buy/7203", json={"quantity": 0, "status": status, "purpose": "swing"})

    assert res.status_code == 200, res.text
    assert res.json()["code"] == "7203.T"
    row = store["df"].set_index("code").loc["7203.T"]
    assert row["status"] == status
    assert row["purpose"] == "swing"


def test_api_default_status_is_purchase(api):
    client, store = api
    res = client.post("/api/actions/buy/7203", json={"quantity": 10})
    assert res.status_code == 200, res.text
    assert store["df"].set_index("code").loc["7203.T", "status"] == StockStatus.HOLDING


@pytest.mark.parametrize(
    "body",
    [
        {"quantity": 0},  # 購入は 1 株以上
        {"quantity": 1, "status": StockStatus.SOLD_PROFIT},  # 登録できない区分
        {"quantity": -1, "status": StockStatus.WATCHING},
    ],
)
def test_api_rejects_invalid_requests(api, body):
    client, _ = api
    assert client.post("/api/actions/buy/7203", json=body).status_code == 400


def test_api_refuses_to_overwrite_held_stock(api):
    client, store = api
    res = client.post("/api/actions/buy/9984", json={"quantity": 0, "status": StockStatus.WATCHING})
    assert res.status_code == 409
    assert store["df"].set_index("code").loc["9984.T", "status"] == StockStatus.HOLDING


# --- チャート一覧 ---------------------------------------------------------------


class _StubGcs:
    use_gcs = True
    CSV = (
        "code,name,quantity,status,purpose,purchase_price,current_price,profit_loss,profit_loss_percent\n"
        "9434.T,SOFTBANK,5,HOLDING,long,100,110,10,10\n"
        "7203.T,TOYOTA,0,WATCHING,swing,100,110,0,10\n"
    )

    def get_file_content(self, path):
        return self.CSV.encode("utf-8") if path == "my_stock.csv" else None

    def list_files(self, prefix):
        return ["9434_ソフトバンク_1mo.png"]  # 7203 はまだチャートが無い


def test_chart_list_includes_stocks_waiting_for_analysis(monkeypatch):
    monkeypatch.setattr(charts, "gcs", _StubGcs())
    listed = {item["code"]: item for item in asyncio.run(charts.list_charts())}

    assert listed["7203"]["analysis_pending"] is True
    assert listed["7203"]["name"] == "TOYOTA"
    assert listed["7203"]["status"] == StockStatus.WATCHING
    assert listed["7203"]["plots"] is None

    assert listed["9434"]["analysis_pending"] is False
    assert listed["9434"]["name"] == "ソフトバンク"  # チャートがある銘柄の表示名は従来どおり


def test_register_choices_are_served_from_backend():
    """登録フォームの区分は /api/choices から配信する (テンプレートに値を書かない / PRIDEV-486)"""
    from python.web import constants

    register = constants.as_client_payload()["register"]
    assert [c["key"] for c in register] == [StockStatus.HOLDING, StockStatus.NEXT_BUY, StockStatus.WATCHING]
    assert [c["purchase"] for c in register] == [True, False, False]
    assert register[1]["label"] == "次回のスイングで購入"
    assert register[2]["label"] == "監視中"
