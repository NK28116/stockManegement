import os
import sys
from unittest.mock import MagicMock, patch


# Mock GCSClient to simulate environments
class MockGCSClient:
    def __init__(self, use_gcs=False, file_exists=False):
        self.use_gcs = use_gcs
        self.file_exists = file_exists

    def get_file_content(self, path):
        if self.use_gcs and path == "my_stock.csv":
            return b"GCS Content" if self.file_exists else None
        if not self.use_gcs and path == "data/my_stock_local.csv":
            return b"Local Content"
        return None


# Test Local Mode
print("--- Testing Local Mode ---")
gcs = MockGCSClient(use_gcs=False)
csv_filename = "my_stock.csv" if gcs.use_gcs else "data/my_stock_local.csv"
csv_content = gcs.get_file_content(csv_filename)
# Logic from charts.py (simplified)
if not gcs.use_gcs and not csv_content:
    print("FALLBACK TRIGGERED (Unexpected for happy path)")
else:
    print(f"Loaded: {csv_filename}, Content: {csv_content}")

# Test GCS Mode (File Missing -> Fallback)
print("\n--- Testing GCS Mode (File Missing) ---")
gcs = MockGCSClient(use_gcs=True, file_exists=False)
csv_filename = "my_stock.csv" if gcs.use_gcs else "data/my_stock_local.csv"
csv_content = gcs.get_file_content(csv_filename)

if gcs.use_gcs and not csv_content:
    print("GCS my_stock.csv not found. Falling back to local data/my_stock.csv")
    # Simulate valid local file
    if os.path.exists("data/my_stock.csv"):
        print("Fallback successful: found data/my_stock.csv")
    else:
        print("Fallback failed: data/my_stock.csv not found on disk")
