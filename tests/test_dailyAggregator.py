import pandas as pd
from unittest.mock import patch, MagicMock
from python.watch import dailyAggregator


@patch("python.watch.dailyAggregator.save_daily_data_to_db")
@patch("python.watch.dailyAggregator.pd.read_sql_query")
@patch("python.watch.dailyAggregator.get_db_connection")
def test_aggregate_intraday_to_daily(mock_conn, mock_read_sql, mock_save):
    # Mock connection and cursor
    conn = MagicMock()
    cur = MagicMock()
    mock_conn.return_value = conn
    conn.cursor.return_value = cur

    # Mock intraday data read
    mock_df = pd.DataFrame([
        {"code": "7203.T", "timestamp": "2025-09-17 09:00:00", "price": 2000, "volume": 100},
        {"code": "7203.T", "timestamp": "2025-09-17 10:00:00", "price": 2100, "volume": 150},
        {"code": "7203.T", "timestamp": "2025-09-17 15:00:00", "price": 2050, "volume": 200},
    ])
    mock_read_sql.return_value = mock_df

    # Run (is_test_mode=False to allow save call, since we mock save function)
    dailyAggregator.aggregate_intraday_to_daily("2025-09-17", is_test_mode=False)

    # Verify save called correct values
    # OHLCV: Open=2000, High=2100, Low=2000, Close=2050, Vol=450
    mock_save.assert_called_once_with(
        "7203.T", "2025-09-17", 
        2000.0, 2100.0, 2000.0, 2050.0, 450
    )
