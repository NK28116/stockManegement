import sys
import os
import pandas as pd
import numpy as np

# Add current dir to path
sys.path.append(os.getcwd())

from python.config import config
from python.utils.indicators import calculate_rsi

print(f"Data Dir: {config.data_dir}")
print(f"Is Data Dir exists: {os.path.exists(config.data_dir)}")

# Test write
test_file = os.path.join(config.data_dir, "test_write.txt")
try:
    with open(test_file, "w") as f:
        f.write("test")
    print(f"Write test success: {test_file}")
    os.remove(test_file)
except Exception as e:
    print(f"Write test failed: {e}")

# Test RSI
prices = pd.Series(np.random.randn(100) + 100)
try:
    rsi = calculate_rsi(prices)
    print(f"RSI calculated. Length: {len(rsi)}")
    print(f"Last RSI: {rsi.iloc[-1]}")
except Exception as e:
    print(f"RSI calculation failed: {e}")
