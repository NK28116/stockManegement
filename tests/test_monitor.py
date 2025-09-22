import sys
import os

import time
import threading
from python.utils import monitor

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_api_call_counter():
    monitor.api_call_count = 0
    monitor.count_api_call()
    monitor.count_api_call()
    assert monitor.api_call_count == 2


def test_log_resource_usage_short_run():
    # 3秒だけ動かして止める
    thread = threading.Thread(target=monitor.log_resource_usage, kwargs={"interval": 1}, daemon=True)
    thread.start()
    time.sleep(3)
    assert thread.is_alive()  # デーモンなので動いている
