# tests/test_portfolio_analyzer.py
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

import sys
import os

# プロジェクトルートを sys.path に追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from python.analysis.portfolio_analyzer import PortfolioAnalyzer


@pytest.fixture
def analyzer(tmp_path):
    """テスト用の PortfolioAnalyzer インスタンス"""
    return PortfolioAnalyzer(result_dir=tmp_path, is_test_mode=True)


@pytest.fixture
def sample_portfolio_df():
    return pd.DataFrame(
        [
            {
                "id": 1,
                "code": "AAPL",
                "name": "Apple",
                "sector": "Tech",
                "quantity": 10,
                "purchase_price": 150,
                "purchase_date": "2024-01-01",
            },
            {
                "id": 2,
                "code": "MSFT",
                "name": "Microsoft",
                "sector": "Tech",
                "quantity": 5,
                "purchase_price": 300,
                "purchase_date": "2024-02-01",
            },
        ]
    )


@patch("python.analysis.portfolio_analyzer.pd.read_sql_query")
@patch("python.analysis.portfolio_analyzer.get_db_connection")
def test_get_portfolio(mock_conn, mock_read_sql, analyzer, sample_portfolio_df):
    mock_read_sql.return_value = sample_portfolio_df

    df = analyzer.get_portfolio("my_stock")
    
    assert not df.empty
    assert "AAPL" in df["code"].values
    assert "Apple" in df["name"].values
    mock_conn.assert_called_once()
    mock_read_sql.assert_called_once()


@patch("python.analysis.portfolio_analyzer.yf.Ticker")
def test_fetch_stock_data(mock_ticker, analyzer):
    mock_stock = MagicMock()
    mock_df = pd.DataFrame({"Close": [100, 101, 102]}, index=pd.date_range("2024-01-01", periods=3))
    mock_stock.history.return_value = mock_df
    mock_ticker.return_value = mock_stock

    df = analyzer.fetch_stock_data("AAPL", period="1mo")
    assert not df.empty
    assert "Close" in df.columns
    mock_ticker.assert_called_once_with("AAPL")


@patch("python.analysis.portfolio_analyzer.calculate_technical_indicators")
@patch("python.analysis.portfolio_analyzer.PortfolioAnalyzer.fetch_stock_data")
@patch("python.analysis.portfolio_analyzer.PortfolioAnalyzer.get_portfolio")
@patch("python.utils.report.send_weekly_report")
def test_analyze_portfolio(
    mock_send_weekly_report, mock_get_portfolio, mock_fetch_stock_data, mock_calc_indicators, analyzer, sample_portfolio_df, tmp_path
):
    # --- Mock 戻り値設定 ---
    mock_get_portfolio.return_value = sample_portfolio_df
    mock_fetch_stock_data.return_value = pd.DataFrame(
        {"Close": [100, 101, 102]}, index=pd.date_range("2024-01-01", periods=3)
    )
    mock_calc_indicators.return_value = pd.DataFrame(
        {
            "bb_middle": [100, 101, 102],
            "bb_upper": [110, 111, 112],
            "bb_lower": [90, 91, 92],
            "macd": [0.1, 0.2, 0.3],
            "macd_signal": [0.05, 0.1, 0.15],
            "macd_dif": [0.05, 0.1, 0.15],
        },
        index=pd.date_range("2024-01-01", periods=3),
    )

    # Execute the test
    analyzer.analyze_portfolio("my_stock")
    
    # Verify that send_weekly_report was called
    mock_send_weekly_report.assert_called_once()

    # 出力ファイルの確認
    output_file = tmp_path / "my_portfolio_analysis.txt"
    assert output_file.exists()
    text = output_file.read_text(encoding="utf-8")
    assert "ポートフォリオ分析レポート" in text
    assert "Apple" in text or "Microsoft" in text


def test_save_analysis(analyzer, sample_portfolio_df, tmp_path):
    # Ensure it writes file
    analyzer.is_test_mode = False
    
    # indicator_dict は空でもよい
    analyzer.save_analysis(sample_portfolio_df, {})
    output_file = tmp_path / "my_portfolio_analysis.txt"
    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "総投資額" in content
