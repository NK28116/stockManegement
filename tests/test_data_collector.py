# tests/test_data_collector.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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


@patch("python.analysis.data_collector.yf.Ticker")
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

    # calculate_indicators calls removed from implementation, just returns df
    result = collector.collect_stock_data("7203")
    
    # Assert result is the dataframe
    pd.testing.assert_frame_equal(result, mock_df)


@patch("yfinance.Ticker")
def test_collect_stock_data_empty(mock_ticker, collector):
    # 空データフレームを返す
    mock_ticker.return_value.history.return_value = pd.DataFrame()
    result = collector.collect_stock_data("INVALID")
    assert result is None


@patch("psycopg2.connect")
def test_get_stock_list_from_db(mock_connect, monkeypatch):
    # Mock DB connection and cursor
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cur
    
    # Mock fetchall result
    mock_cur.fetchall.return_value = [("7203",), ("6758",)]

    codes = dc.get_stock_list_from_db()
    
    assert codes == ["7203", "6758"]
    mock_cur.execute.assert_called_with("SELECT code FROM stocks")


@patch.object(dc, "get_stock_list_from_db", return_value=["7203"])
@patch.object(dc.StockDataCollector, "fetch_and_store_prices", return_value=None)
@patch.object(dc.StockDataCollector, "collect_stock_data")
def test_main(mock_collect, mock_fetch, mock_get_list, tmp_path, monkeypatch):
    monkeypatch.setattr(dc.config, "data_dir", str(tmp_path))
    # Return a DataFrame to simulate successful collection
    mock_df = pd.DataFrame({"売上": [100]})
    mock_collect.return_value = mock_df
    # No need to patch db_path anymore as it's not used directly in main logic (handled via get_stock_list_from_db and fetch_and_store_prices)

    dc.main()

    output_file = tmp_path / "quarterly_data_collection.csv"
    assert output_file.exists()
    df = pd.read_csv(output_file, skiprows=1)
    assert "売上" in df.columns
