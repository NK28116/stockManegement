import sys
import os

# Unset env vars to test default behavior
if "LOCAL_PG_PORT" in os.environ:
    del os.environ["LOCAL_PG_PORT"]
if "CLOUD_PG_PORT" in os.environ:
    del os.environ["CLOUD_PG_PORT"]

try:
    from python.config import config

    print("Configuration loaded successfully.")
    print(f"DB Config: {config.get_db_config()}")
except Exception as e:
    print(f"Configuration failed: {e}")
    sys.exit(1)
