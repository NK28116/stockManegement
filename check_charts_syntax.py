import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

try:
    from python.web.routes import charts

    print("✅ Successfully imported charts module")
except Exception as e:
    print(f"❌ Failed to import charts module: {e}")
    exit(1)
