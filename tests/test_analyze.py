# tests/test_analyze.py
import sqlite3
from unittest.mock import patch
import pytest

from python.watch.analyze import get_daily_price_data, analyze_daily_data


@pytest.fixture
def setup_db(tmp_path):
    """テスト用SQLite DBをセットアップ"""
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE stock_data (
            date TEXT,
            code TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER
        )
        """
    )
    # サンプルデータ挿入（2日分）
    cur.executemany(
        "INSERT INTO stock_data VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("2025-09-17", "TEST", 100, 110, 90, 100, 1000),
            ("2025-09-18", "TEST", 100, 105, 95, 80, 1200),
        ],
    )
    conn.commit()
    conn.close()
    return str(db_file)


def test_get_daily_price_data(setup_db, monkeypatch):
    monkeypatch.setattr("python.watch.analyze.DB_PATH", setup_db)

    df = get_daily_price_data("TEST", limit=10)
    assert not df.empty
    assert "close" in df.columns
    assert df.iloc[-1]["close"] == 80


@patch("python.utils.alert.send_alert")
def test_analyze_daily_data_crash(mock_send_alert, setup_db, monkeypatch):
    """急落検知で send_alert が呼ばれるか"""
    monkeypatch.setattr("python.watch.analyze.DB_PATH", setup_db)

    analyze_daily_data("TEST")

    mock_send_alert.assert_called_once()
    args, kwargs = mock_send_alert.call_args
    assert "下落" in args[0]  # メッセージ内に「下落」が含まれること


@patch("python.watch.analyze.calculate_macd")
def test_analyze_daily_data_macd(mock_macd, setup_db, monkeypatch, caplog):
    monkeypatch.setattr("python.watch.analyze.DB_PATH", setup_db)
    # MACD期間を短く設定してテストが実行されるようにする
    monkeypatch.setattr("python.watch.analyze.config.macd_long_period", 2)
    
    # MACDダミー計算結果を返す
    df = get_daily_price_data("TEST")
    df["macd"] = [0, 1]
    df["macd_signal"] = [1, 0]
    mock_macd.return_value = df

    with caplog.at_level("INFO"):
        analyze_daily_data("TEST")

    assert any("MACDゴールデンクロス" in m for m in caplog.messages)


@patch("python.watch.analyze.calculate_bollinger_bands")
def test_analyze_daily_data_bollinger(mock_bb, setup_db, monkeypatch, caplog):
    monkeypatch.setattr("python.watch.analyze.DB_PATH", setup_db)
    # ボリンジャーバンド期間を短く設定してテストが実行されるようにする
    monkeypatch.setattr("python.watch.analyze.config.bollinger_period", 2)
    
    df = get_daily_price_data("TEST")
    # 終値が80なので、ローワーバンドを上回るように設定して条件をトリガーさせる
    df["upper_band"] = [90, 90]
    df["lower_band"] = [85, 85]  # 80 < 85にしてローワーバンド下抹けをトリガー
    mock_bb.return_value = df

    with caplog.at_level("INFO"):
        analyze_daily_data("TEST")

    assert any("アッパーバンド" in m or "ローワーバンド" in m for m in caplog.messages)
