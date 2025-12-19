import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from python.secret_manager import secret_manager
from python.utils.logger import get_logger
from python.config import config


def test_secret_manager_fallback():
    print("--- Testing Secret Manager Fallback ---")
    # Set a dummy env var
    test_key = "TEST_SECRET_KEY"
    test_value = "dummy_value"
    os.environ[test_key] = test_value

    # Try to get it via secret manager
    val = secret_manager.get_secret(test_key, default="fallback")
    print(f"Env Var '{test_key}': {val}")

    if val == test_value:
        print("[PASS] Secret Manager correctly retrieved env var.")
    else:
        print(f"[FAIL] Expected {test_value}, got {val}")

    # Try non-existent key
    val_missing = secret_manager.get_secret("MISSING_KEY_12345", default="default_val")
    print(f"Missing Key: {val_missing}")
    if val_missing == "default_val":
        print("[PASS] Default value returned for missing key.")
    else:
        print(f"[FAIL] Expected 'default_val', got {val_missing}")


def test_logger_initialization():
    print("\n--- Testing Logger Initialization ---")

    # Test logger creation
    logger = get_logger("test_module", category="test_category")
    logger.info("This is a test log message from verify_security.py")

    # Check if log file exists (Local mode)
    if not os.getenv("GOOGLE_CLOUD_PROJECT"):
        # Expect local file
        log_dir = config.log_dir / "test_category" / "test_module"
        log_files = list(log_dir.glob("*.log"))
        if log_files:
            print(f"[PASS] Log file created at {log_files[0]}")
        else:
            print(f"[FAIL] No log file created in {log_dir}")
    else:
        print("[INFO] Skipping file check (Cloud Mode detected)")


if __name__ == "__main__":
    test_secret_manager_fallback()
    test_logger_initialization()
