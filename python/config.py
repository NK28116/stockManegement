# python/config.py
"""
設定ファイル
環境変数やパラメータを管理
"""

import os
from pathlib import Path
from typing import Any, Dict


class Config:
    """設定管理クラス"""

    def __init__(self):
        # ルートディレクトリ
        self.root_dir = Path(__file__).resolve().parent.parent

        # 固定パス
        self.codes_path = self.root_dir / "data" / "my_stock.csv"
        self.data_dir = self.root_dir / "data"
        self.log_dir = self.root_dir / "log"
        self.archive_dir = self.root_dir / "data" / "archive"

        # DB接続設定 (切り替え)
        self.db_env = os.getenv("DB_ENV", "local")

        # 分析・リスク管理・監視パラメータ（省略：既存コードそのまま）
        self.default_period = "1mo"
        self.ma_short = 5
        self.ma_long = 25
        self.volatility_period = 10
        self.max_loss_percent = 3.0
        self.risk_per_trade = 1.0
        self.take_profit_percent = 8.0
        self.stop_loss_percent = 0.05
        self.take_profit_percent = 0.10
        self.trailing_stop_percent = 0.03
        self.crash_threshold = -3.0
        self.volatility_threshold = 3.0
        self.volume_spike_threshold = 2.0
        self.rsi_overbought_threshold = 70.0
        self.rsi_oversold_threshold = 30.0
        self.macd_fast_period = 12
        self.macd_slow_period = 26
        self.macd_long_period = 26
        self.macd_signal_period = 9
        self.bollinger_period = 20
        self.bollinger_std = 2
        self.risk_free_rate = 0.001
        self.default_portfolio_file = self.root_dir / "data" / "my_stock.csv"

        # アラート設定
        self.slack_webhook = os.getenv("SLACK_WEBHOOK", "")

        # 証券会社API
        self.XXXX_API_KEY = os.getenv("XXXX_API_KEY", "")
        self.XXXX_API_SECRET = os.getenv("XXXX_API_SECRET", "")
        self.XXXX_API_URL = os.getenv("XXXX_API_URL", "")

    def get_db_config(self) -> Dict[str, Any]:
        """DB接続設定を環境に応じて返す"""
        if self.db_env == "cloud":
            return {
                "host": os.getenv("CLOUD_PG_HOST", "localhost"),
                "port": int(os.getenv("CLOUD_PG_PORT", "5432")),
                "database": os.getenv("CLOUD_PG_DATABASE", "stock_db"),
                "user": os.getenv("CLOUD_PG_USER"),
                "password": os.getenv("CLOUD_PG_PASSWORD"),
            }
        else:  # default local
            return {
                "host": os.getenv("LOCAL_PG_HOST", "localhost"),
                "port": int(os.getenv("LOCAL_PG_PORT", "5432")),
                "database": os.getenv("LOCAL_PG_DATABASE", "stock_db"),
                "user": os.getenv("LOCAL_PG_USER", "stock_user"),
                "password": os.getenv("LOCAL_PG_PASSWORD", ""),
            }

    def get_watch_config(self) -> Dict[str, Any]:
        return {
            "crash_threshold": self.crash_threshold,
            "volatility_threshold": self.volatility_threshold,
            "volume_spike_threshold": self.volume_spike_threshold,
        }

    def get_alert_config(self) -> Dict[str, Any]:
        return {"slack_webhook": self.slack_webhook, "enabled": bool(self.slack_webhook)}

    def get_trade_config(self) -> Dict[str, Any]:
        return {"risk_per_trade": self.risk_per_trade, "max_loss_percent": self.max_loss_percent}


# 共通インスタンス
config = Config()
