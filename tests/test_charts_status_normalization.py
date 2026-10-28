"""チャート一覧 API が旧ステータスを英字キーへ正規化して返すことのテスト (PRIDEV-524)

本番は GCS 上の my_stock.csv を直接読む。移行スクリプトの適用前後で
旧日本語ステータスが残っていても、画面が誤った保有表示をしないことを確かめる。
GCS クライアントはスタブへ差し替える。
"""

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from python.trading.stock_status import StockStatus, is_held  # noqa: E402
from python.web.routes import charts  # noqa: E402

CSV = (
    "code,name,quantity,status,purpose,purchase_price,current_price,profit_loss,profit_loss_percent\n"
    "9434.T,A,5,保有中,long,100,110,10,10\n"
    "9193.T,B,1,売却（利益確定）,middle,100,110,10,10\n"
    "6503.T,C,0,売却（利益確定）,middle,100,110,10,10\n"
    "5020.T,D,,売却（損切り）,middle,100,110,10,10\n"
    "7203.T,E,1,HOLDING,swing,100,110,10,10\n"
    "1234.T,F,1,売却,swing,100,110,10,10\n"
)


class _StubGcs:
    use_gcs = True

    def get_file_content(self, path):
        return CSV.encode("utf-8") if path == "my_stock.csv" else None

    def list_files(self, prefix):
        codes = ["9434", "9193", "6503", "5020", "7203", "1234"]
        return [f"{code}_name_1mo.png" for code in codes]


@pytest.fixture
def listed(monkeypatch):
    monkeypatch.setattr(charts, "gcs", _StubGcs())
    return {item["code"]: item for item in asyncio.run(charts.list_charts())}


def test_legacy_statuses_are_returned_as_canonical_keys(listed):
    assert listed["9434"]["status"] == StockStatus.HOLDING
    assert listed["9193"]["status"] == StockStatus.SELL_PLANNED_PROFIT
    assert listed["6503"]["status"] == StockStatus.SOLD_PROFIT
    assert listed["7203"]["status"] == StockStatus.HOLDING


def test_unresolvable_statuses_are_not_shown_as_held(listed):
    # 数量欠損の旧売却ラベル / 区別の無い「売却」は推測せず元の値のまま返す
    assert listed["5020"]["status"] == "売却（損切り）"
    assert listed["1234"]["status"] == "売却"
    assert not is_held(listed["5020"]["status"])
    assert not is_held(listed["1234"]["status"])
