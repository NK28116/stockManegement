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


# --- 銘柄コードの表記ゆれ (画面は 7203、保存データは 7203.T) ---------------------


@pytest.mark.parametrize("raw", ["7203", "7203.T", "7203_T", " 7203.t "])
def test_code_key_ignores_suffix(raw):
    assert bss.code_key(raw) == "7203"


def test_find_rows_matches_screen_code():
    df = _df(["7203.T", "T", 100, 1000.0, "2026-01-01", "", StockStatus.HOLDING])
    assert list(bss.find_rows(df, "7203")) == [0]


@pytest.fixture
def store(monkeypatch):
    """load_codes / save_codes をメモリ上の DataFrame に差し替える"""
    data = {
        "df": _df(
            ["7203.T", "TOYOTA", 100, 1000.0, "2026-01-01", "long", StockStatus.HOLDING],
            ["6758", "SONY", 0, 0.0, "2026-01-01", "", StockStatus.WATCHING],  # 古い表記の行
        )
    }
    monkeypatch.setattr(bss, "load_codes", lambda path: data["df"].copy())
    monkeypatch.setattr(bss, "save_codes", lambda df, path: data.update(df=df))
    return data


def test_delete_accepts_code_without_suffix(store):
    """画面から送られる 7203 で、保存データの 7203.T を削除できる"""
    result = bss.delete_stock("7203")
    assert "error" not in result
    assert list(store["df"]["code"]) == ["6758"]


def test_sell_accepts_code_without_suffix(store):
    result = bss.sell_stock("7203", "profit")
    assert "error" not in result
    assert store["df"].iloc[0]["status"] == StockStatus.SOLD_PROFIT


def test_buy_normalizes_legacy_code(store):
    df = bss.buy(store["df"], "6758.T", 10, 3000.0)
    assert list(df["code"]) == ["7203.T", "6758.T"]  # 行は増えず、表記だけそろう
    assert df.iloc[1]["status"] == StockStatus.HOLDING


# --- 保有銘柄の更新 ---------------------------------------------------------------


def test_update_stock_changes_given_fields_only(store):
    df = bss.update_stock(store["df"], "7203", {"quantity": 50, "purchase_price": 1234.567})
    row = df.iloc[0]
    assert row["quantity"] == 50
    assert row["purchase_price"] == 1234.57
    assert row["purchase_date"] == "2026-01-01"
    assert row["purpose"] == "long"


@pytest.mark.parametrize(
    "changes",
    [
        {"quantity": -1},
        {"purchase_price": -1},
        {"purchase_date": "2026/01/01"},
        {"status": "UNKNOWN"},
        {"quantity": 0},  # 保有中のまま株数 0 にはできない
    ],
)
def test_update_stock_rejects_invalid_values(store, changes):
    with pytest.raises(ValueError):
        bss.update_stock(store["df"], "7203", changes)


def test_update_stock_can_mark_as_sell_planned(store):
    df = bss.update_stock(store["df"], "7203", {"status": StockStatus.SELL_PLANNED_PROFIT})
    assert df.iloc[0]["status"] == StockStatus.SELL_PLANNED_PROFIT


def test_update_stock_unknown_code(store):
    with pytest.raises(KeyError):
        bss.update_stock(store["df"], "9999", {"quantity": 1})


@pytest.fixture
def client(store):
    app = FastAPI()
    app.include_router(actions.router)
    return TestClient(app)


def test_api_update_stock(client, store):
    res = client.put("/api/actions/stock/7203", json={"quantity": 30, "purpose": "swing"})
    assert res.status_code == 200, res.text
    assert res.json()["item"]["quantity"] == "30"
    assert store["df"].iloc[0]["purpose"] == "swing"


@pytest.mark.parametrize(
    "code,body,expected",
    [
        ("9999", {"quantity": 1}, 404),
        ("7203", {}, 400),
        ("7203", {"purpose": "unknown"}, 400),
        ("7203", {"quantity": -5}, 400),
    ],
)
def test_api_update_stock_errors(client, code, body, expected):
    assert client.put(f"/api/actions/stock/{code}", json=body).status_code == expected


def test_api_delete_with_screen_code(client, store):
    assert client.delete("/api/actions/stock/7203").status_code == 200
    assert "7203.T" not in list(store["df"]["code"])


def test_api_sell_error_is_400_not_500(client):
    res = client.post("/api/actions/sell/9999", json={"sell_type": "profit"})
    assert res.status_code == 400


def test_api_register_returns_row_for_immediate_display(client):
    res = client.post("/api/actions/buy/9984", json={"quantity": 10})
    assert res.status_code == 200, res.text
    item = res.json()["item"]
    assert item["code"] == "9984"  # 一覧と同じ表記
    assert item["status"] == StockStatus.HOLDING
    assert item["quantity"] == "10"


# --- 保存の失敗を成功扱いにしない -------------------------------------------------


def test_save_codes_raises_when_gcs_upload_fails(monkeypatch, tmp_path):
    class _Blob:
        def upload_from_string(self, *a, **k):
            raise RuntimeError("403 Forbidden")

    class _Bucket:
        def blob(self, name):
            return _Blob()

    class _Gcs:
        use_gcs = True
        bucket = _Bucket()

    monkeypatch.setattr(bss, "gcs", _Gcs())
    local = tmp_path / "my_stock.csv"
    with pytest.raises(RuntimeError):
        bss.save_codes(_df(), str(local))
    assert not local.exists()  # ローカルへこっそり保存しない


# --- チャート一覧は my_stock.csv が正 ------------------------------------------------


class _StubGcsWithOrphan(_StubGcs):
    def list_files(self, prefix):
        # 1111 は削除済み (CSV に無い) 銘柄の古いチャート
        return ["9434_ソフトバンク_1mo.png", "1111_テスト_1mo.png"]


def test_chart_list_hides_charts_of_deleted_stocks(monkeypatch):
    monkeypatch.setattr(charts, "gcs", _StubGcsWithOrphan())
    codes = {item["code"] for item in asyncio.run(charts.list_charts())}
    assert codes == {"9434", "7203"}


def test_chart_list_falls_back_to_charts_when_csv_is_unavailable(monkeypatch):
    class _NoCsv(_StubGcsWithOrphan):
        def get_file_content(self, path):
            return None

    monkeypatch.setattr(charts, "gcs", _NoCsv())
    monkeypatch.chdir("/")  # ローカルの data/my_stock.csv を読まないようにする
    codes = {item["code"] for item in asyncio.run(charts.list_charts())}
    assert codes == {"9434", "1111"}


def test_chart_list_shows_status_of_row_without_prices(monkeypatch):
    """購入直後の行 (current_price などが空欄) も、ステータス・株数付きで返す"""

    class _NewRow(_StubGcs):
        CSV = (
            "code,name,quantity,purchase_price,purchase_date,purpose,status,current_price,profit_loss,profit_loss_percent\n"
            "9434.T,SOFTBANK,5,100,2026-01-01,long,HOLDING,110,10,10%\n"
            "4755.T,RAKUTEN,10,,2026-10-29,swing,HOLDING,,,\n"
        )

    monkeypatch.setattr(charts, "gcs", _NewRow())
    listed = {item["code"]: item for item in asyncio.run(charts.list_charts())}
    assert listed["4755"]["status"] == StockStatus.HOLDING
    assert listed["4755"]["quantity"] == "10"
    assert listed["4755"]["analysis_pending"] is True
