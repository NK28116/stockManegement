# tests/test_analyze.py
import pandas as pd
from unittest.mock import patch, MagicMock
import pytest

from python.watch.analyze import get_daily_price_data, analyze_daily_data


@patch("python.watch.analyze.pd.read_sql_query")
@patch("python.watch.analyze.get_db_connection")
def test_get_daily_price_data(mock_conn, mock_read_sql):
    # Mock return value
    mock_df = pd.DataFrame({
        "close": [80],
        "open": [100],
        "high": [110],
        "low": [90],
        "volume": [1000]
    }, index=pd.to_datetime(["2025-09-18"]))
    mock_read_sql.return_value = mock_df

    df = get_daily_price_data("TEST", limit=10)
    
    assert not df.empty
    assert "close" in df.columns
    assert df.iloc[-1]["close"] == 80
    mock_conn.assert_called_once()


@patch("python.watch.analyze.send_alert")
@patch("python.watch.analyze.get_daily_price_data")
def test_analyze_daily_data_crash(mock_get_data, mock_send_alert, monkeypatch):
    """急落検知で send_alert が呼ばれるか"""
    # Mock data with a crash
    mock_df = pd.DataFrame({
        "close": [100, 80], # 20% drop
    }, index=pd.to_datetime(["2025-09-17", "2025-09-18"]))
    mock_get_data.return_value = mock_df
    
    # Ensure config triggers crash
    monkeypatch.setattr("python.watch.analyze.config.crash_threshold", -10.0)

    analyze_daily_data("TEST", "Test Name")

    mock_send_alert.assert_called_once()
    args, kwargs = mock_send_alert.call_args
    assert "下落" in args[0] or "急落" in args[0]


@patch("python.watch.analyze.logger")
@patch("python.watch.analyze.calculate_macd")
@patch("python.watch.analyze.get_daily_price_data")
def test_analyze_daily_data_macd(mock_get_data, mock_macd, mock_logger, monkeypatch):
    # Mock data
    mock_df = pd.DataFrame({
        "close": [100, 100], 
    }, index=pd.to_datetime(["2025-09-17", "2025-09-18"]))
    mock_get_data.return_value = mock_df

    # MACD期間を短く設定してテストが実行されるようにする
    monkeypatch.setattr("python.watch.analyze.config.macd_long_period", 2)
    
    # ゴールデンクロス: prev(macd <= signal) -> current(macd > signal)
    mock_df_macd = mock_df.copy()
    mock_df_macd["macd"] = [0, 1]
    mock_df_macd["macd_signal"] = [0.5, 0.5] 
    mock_macd.return_value = mock_df_macd

    analyze_daily_data("TEST", "Test Name")

    # Check if any info log contains "MACDゴールデンクロス"
    assert any("MACDゴールデンクロス" in call.args[0] for call in mock_logger.info.call_args_list)


@patch("python.watch.analyze.logger")
@patch("python.watch.analyze.calculate_bollinger_bands")
@patch("python.watch.analyze.get_daily_price_data")
def test_analyze_daily_data_bollinger(mock_get_data, mock_bb, mock_logger, monkeypatch):
    # Mock data
    mock_df = pd.DataFrame({
        "close": [85, 80], 
    }, index=pd.to_datetime(["2025-09-17", "2025-09-18"]))
    mock_get_data.return_value = mock_df

    # ボリンジャーバンド期間を短く設定してテストが実行されるようにする
    monkeypatch.setattr("python.watch.analyze.config.bollinger_period", 2)
    
    # ボリンジャーバンドダミー計算結果
    # ローワーバンド下抜け: close < lower_band
    mock_df_bb = mock_df.copy()
    mock_df_bb["upper_band"] = [100, 100]
    mock_df_bb["lower_band"] = [90, 85] # 80 < 85 -> 下抜け
    mock_bb.return_value = mock_df_bb

    analyze_daily_data("TEST", "Test Name")

    assert any(("アッパーバンド" in call.args[0] or "ローワーバンド" in call.args[0]) for call in mock_logger.info.call_args_list)
