import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

try:
    print("Attempting to import python.web.app...")
    from python.web.app import app
    print("Successfully imported python.web.app")
    print(f"App title: {app.title}")
except ImportError as e:
    print(f"Failed to import: {e}")
    sys.exit(1)
except Exception as e:
    print(f"An error occurred: {e}")
    sys.exit(1)
