import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import io

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import modules to test
# We need to patch imports BEFORE they are used in the modules if we want to mock module-level variables like 'gcs'
# However, 'gcs' is imported FROM python.utils.gcs_client.
# So we can patch `python.utils.gcs_client.gcs`

from python.trading import buy_and_sell_stock
from python.visualization.stock_chart_visualizer import StockChartVisualizer
from python.utils.gcs_client import gcs


class TestGCSSync(unittest.TestCase):
    def setUp(self):
        # Create a sample DataFrame
        self.df = pd.DataFrame(
            {
                "code": ["7203", "9984"],
                "name": ["Toyota", "Softbank"],
                "status": ["active", "watch"],
                "purpose": ["investment", "speculation"],
                "quantity": [100, 200],
                "purchase_price": [2000, 5000],
                "purchase_date": ["2023-01-01", "2023-01-02"],
            }
        )
        self.csv_content = self.df.to_csv(index=False).encode("utf-8")

    def test_save_codes_gcs(self):
        print("\nTesting save_codes with GCS enabled...")
        with patch("python.trading.buy_and_sell_stock.gcs") as mock_gcs:
            mock_gcs.use_gcs = True
            mock_blob = MagicMock()
            mock_gcs.bucket.blob.return_value = mock_blob

            buy_and_sell_stock.save_codes(self.df, "dummy_path")

            mock_gcs.bucket.blob.assert_called_with("my_stock.csv")
            mock_blob.upload_from_string.assert_called_once()
            print("OK: save_codes called upload_from_string")

    def test_load_codes_gcs(self):
        print("\nTesting load_codes with GCS enabled...")
        with patch("python.trading.buy_and_sell_stock.gcs") as mock_gcs:
            mock_gcs.use_gcs = True
            mock_gcs.get_file_content.return_value = self.csv_content

            df_loaded = buy_and_sell_stock.load_codes("dummy_path")

            mock_gcs.get_file_content.assert_called_with("my_stock.csv")
            self.assertEqual(len(df_loaded), 2)
            self.assertEqual(df_loaded.iloc[0]["code"], 7203)  # pandas infers int
            print("OK: load_codes loaded data from GCS content")

    def test_visualizer_load_portfolio_gcs(self):
        print("\nTesting StockChartVisualizer.load_portfolio_stocks with GCS enabled...")
        visualizer = StockChartVisualizer()

        # We need to patch where StockChartVisualizer imports gcs
        with patch("python.visualization.stock_chart_visualizer.gcs") as mock_gcs:
            mock_gcs.use_gcs = True
            mock_gcs.get_file_content.return_value = self.csv_content

            stocks = visualizer.load_portfolio_stocks("my_stock.csv")

            mock_gcs.get_file_content.assert_called_with("my_stock.csv")
            self.assertEqual(len(stocks), 2)
            self.assertEqual(stocks[0]["code"], 7203)
            print("OK: load_portfolio_stocks loaded data from GCS content")


if __name__ == "__main__":
    unittest.main()
