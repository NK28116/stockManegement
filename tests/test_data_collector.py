# tests/test_data_collector.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import sqlite3
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

import python.analysis.data_collector as dc


@pytest.fixture
def collector():
    return dc.StockDataCollector()


def test_get_last_quarter_dates(collector):
    start, end = collector._get_last_quarter_dates()
    # フォーマットがYYYY-MM-DDになっていることを確認
    assert len(start) == 10
    assert len(end) == 10
    assert "-" in start and "-" in end


def test_get_four_quarter_dates(collector):
    start, end = collector._get_four_quarter_dates()
    assert len(start) == 10
    assert len(end) == 10


@patch("yfinance.Ticker")
def test_collect_stock_data_success(mock_ticker, collector):
    # yfinance の戻り値をモック
    mock_df = pd.DataFrame(
        {
            "Open": [100, 101],
            "High": [110, 111],
            "Low": [90, 91],
            "Close": [105, 106],
            "Volume": [1000, 2000],
        },
        index=pd.date_range("2024-01-01", periods=2),
    )
    mock_ticker.return_value.history.return_value = mock_df

    # calculate_indicators, analyze_performance をモック
    collector.calculate_indicators = MagicMock(return_value=mock_df)
    collector.analyze_performance = MagicMock(return_value={"performance": 123})

    result = collector.collect_stock_data("7203")
    assert result == {"performance": 123}
    collector.calculate_indicators.assert_called_once()
    collector.analyze_performance.assert_called_once()


@patch("yfinance.Ticker")
def test_collect_stock_data_empty(mock_ticker, collector):
    # 空データフレームを返す
    mock_ticker.return_value.history.return_value = pd.DataFrame()
    result = collector.collect_stock_data("INVALID")
    assert result is None


def test_get_stock_list_from_db(tmp_path, monkeypatch):
    # 一時DBを作成
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("CREATE TABLE stocks (code TEXT)")
    cur.executemany("INSERT INTO stocks (code) VALUES (?)", [("7203",), ("6758",)])
    conn.commit()
    conn.close()

    # config.db_path を差し替え
    monkeypatch.setattr(dc.config, "db_path", str(db_path))

    codes = dc.get_stock_list_from_db()
    assert codes == ["7203", "6758"]


@patch.object(dc, "get_stock_list_from_db", return_value=["7203"])
@patch.object(dc.StockDataCollector, "fetch_and_store_prices", return_value=None)
@patch.object(dc.StockDataCollector, "collect_stock_data", return_value={"売上": 100})
def test_main(mock_collect, mock_fetch, mock_get_list, tmp_path, monkeypatch):
    monkeypatch.setattr(dc.config, "data_dir", str(tmp_path))
    monkeypatch.setattr(dc.config, "db_path", str(tmp_path / "dummy.db"))

    dc.main()

    output_file = tmp_path / "quarterly_data_collection.csv"
    assert output_file.exists()
    df = pd.read_csv(output_file)
    assert "売上" in df.columns
