"""GET /api/signals/latest: 登録中の銘柄だけを返し、保有中かどうかは登録データから判定する"""

from datetime import date, datetime

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from python.db.models import Base, Signal
from python.trading import buy_and_sell_stock as bss
from python.trading.stock_status import StockStatus
from python.web.api import signals


@pytest.fixture
def client(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'signals.db'}")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        for symbol, score in (
            ("7203.T", 6),
            ("7326.T", 5),
            ("1111.T", 7),
        ):  # 1111 は削除済み
            session.add(
                Signal(
                    symbol=symbol,
                    analysis_date=date(2026, 10, 29),
                    signal_type="LONG",
                    score=score,
                    detected_patterns="[]",
                    created_at=datetime(2026, 10, 29, 7, 0),
                )
            )
        session.commit()
    monkeypatch.setattr(signals, "engine", engine)

    app = FastAPI()
    app.include_router(signals.router)
    return TestClient(app)


def _portfolio(monkeypatch, rows):
    df = pd.DataFrame(rows, columns=["code", "quantity", "status"])
    monkeypatch.setattr(bss, "load_codes", lambda path: df.copy())


def test_deleted_stocks_are_not_returned(client, monkeypatch):
    _portfolio(
        monkeypatch,
        [["7203.T", 100, StockStatus.HOLDING], ["7326", 0, StockStatus.WATCHING]],
    )
    symbols = {s["symbol"] for s in client.get("/api/signals/latest").json()}
    assert symbols == {"7203.T", "7326.T"}


def test_held_flag_comes_from_registered_status(client, monkeypatch):
    _portfolio(
        monkeypatch,
        [["7203.T", 100, StockStatus.HOLDING], ["7326.T", 0, StockStatus.WATCHING]],
    )
    held = {s["symbol"]: s["is_held"] for s in client.get("/api/signals/latest").json()}
    assert held == {"7203.T": True, "7326.T": False}


def test_returns_all_signals_when_portfolio_cannot_be_read(client, monkeypatch):
    def broken(path):
        raise RuntimeError("GCS unavailable")

    monkeypatch.setattr(bss, "load_codes", broken)
    symbols = {s["symbol"] for s in client.get("/api/signals/latest").json()}
    assert symbols == {"7203.T", "7326.T", "1111.T"}
