# python/config.py
"""
設定ファイル
環境変数やパラメータを管理
"""

import os
from pathlib import Path
from typing import Any, Dict

import dotenv

from python.secret_manager import secret_manager
from python.trading.rules import indicator_settings, risk_management

dotenv.load_dotenv()  # .envファイルの読み込み


class Config:
    """設定管理クラス"""

    def __init__(self):
        # ルートディレクトリ
        self.root_dir = Path(__file__).resolve().parent.parent

        # 固定パス
        self.data_dir = self.root_dir / "data"
        self.log_dir = self.root_dir / "log"
        self.archive_dir = self.root_dir / "data" / "archive"

        # DB接続設定 (切り替え) -- codes_path より先に読む
        self.db_env = os.getenv("DB_ENV", "local")

        # DB_ENV に応じて参照する株式ポートフォリオ CSV を切り替える
        # local: ローカル開発用CSV、cloud: GCE/ステージング用CSV
        _csv_filename = "my_stock_local.csv" if self.db_env == "local" else "my_stock.csv"
        self.codes_path = self.root_dir / "data" / _csv_filename

        # 分析パラメータ（定数は python/trading/rules/ から参照）
        self.default_period = "1mo"
        self.ma_short = indicator_settings.EMA_SHORT_PERIOD
        self.ma_long = indicator_settings.EMA_LONG_PERIOD
        self.volatility_period = 10
        self.max_loss_percent = risk_management.MAX_DAILY_LOSS_PCT * 100
        self.risk_per_trade = risk_management.RISK_PER_TRADE * 100
        self.stop_loss_percent = risk_management.STOP_LOSS_PERCENT_LEGACY
        self.take_profit_percent = risk_management.TAKE_PROFIT_PERCENT_LEGACY
        self.trailing_stop_percent = risk_management.TRAILING_STOP_PERCENT
        self.crash_threshold = indicator_settings.CRASH_THRESHOLD_PCT
        self.volatility_threshold = indicator_settings.VOLATILITY_THRESHOLD_PCT
        self.volume_spike_threshold = indicator_settings.VOLUME_SPIKE_THRESHOLD
        self.rsi_overbought_threshold = float(indicator_settings.RSI_OVERBOUGHT)
        self.rsi_oversold_threshold = float(indicator_settings.RSI_OVERSOLD)
        self.macd_fast_period = indicator_settings.MACD_FAST_PERIOD
        self.macd_slow_period = indicator_settings.MACD_SLOW_PERIOD
        self.macd_long_period = indicator_settings.MACD_SLOW_PERIOD
        self.macd_signal_period = indicator_settings.MACD_SIGNAL_PERIOD
        self.bollinger_period = indicator_settings.BOLLINGER_PERIOD
        self.bollinger_std = indicator_settings.BOLLINGER_STD
        self.risk_free_rate = 0.001
        self.default_portfolio_file = self.root_dir / "data" / "my_stock.csv"

        # アラート設定
        self.slack_webhook = secret_manager.get_secret("SLACK_WEBHOOK", os.getenv("SLACK_WEBHOOK", "{SLACK_WEBHOOK}"))
        self.slack_bot_token = secret_manager.get_secret("SLACK_BOT_TOKEN", os.getenv("SLACK_BOT_TOKEN", ""))
        self.slack_channel = secret_manager.get_secret("SLACK_CHANNEL", os.getenv("SLACK_CHANNEL", ""))

        # 証券会社API
        self.XXXX_API_KEY = secret_manager.get_secret("XXXX_API_KEY", os.getenv("XXXX_API_KEY", ""))
        self.XXXX_API_SECRET = secret_manager.get_secret("XXXX_API_SECRET", os.getenv("XXXX_API_SECRET", ""))

        # バックグラウンドタスク間隔設定 (秒)
        self.watch_interval_seconds = int(os.getenv("WATCH_INTERVAL_SECONDS", "120"))  # 2分
        self.analyze_interval_seconds = int(os.getenv("ANALYZE_INTERVAL_SECONDS", "3600"))  # 1時間
        self.monitor_interval_seconds = int(os.getenv("MONITOR_INTERVAL_SECONDS", "7200"))  # 2時間

        # Matplotlib フォント設定
        self.matplotlib_font_family = os.getenv("MATPLOTLIB_FONT_FAMILY", "IPAexGothic")

    def get_db_config(self) -> Dict[str, Any]:
        """DB接続設定を環境に応じて返す"""
        if self.db_env == "cloud":
            return {
                "host": os.getenv("CLOUD_PG_HOST", "{CLOUD_PG_HOST}"),
                "port": int(os.getenv("CLOUD_PG_PORT", "5432")),
                "database": os.getenv("CLOUD_PG_DATABASE", "{CLOUD_PG_DATABASE}"),
                "user": os.getenv("CLOUD_PG_USER", "{CLOUD_PG_USER}"),
                "password": os.getenv("CLOUD_PG_PASSWORD", "{CLOUD_PG_PASSWORD}"),
                # 任意: require / verify-full 等。未設定なら付与しない（ローカルProxy互換）
                "sslmode": os.getenv("CLOUD_PG_SSLMODE"),
            }
        else:  # default local
            return {
                "host": os.getenv("LOCAL_PG_HOST", "{LOCAL_PG_HOST}"),
                "port": int(os.getenv("LOCAL_PG_PORT", "5432")),
                "database": os.getenv("LOCAL_PG_DATABASE", "{LOCAL_PG_DATABASE}"),
                "user": os.getenv("LOCAL_PG_USER", "{LOCAL_PG_USER}"),
                "password": os.getenv("LOCAL_PG_PASSWORD", "{LOCAL_PG_PASSWORD}"),
            }

    def get_watch_config(self) -> Dict[str, Any]:
        return {
            "crash_threshold": self.crash_threshold,
            "volatility_threshold": self.volatility_threshold,
            "volume_spike_threshold": self.volume_spike_threshold,
        }

    def get_alert_config(self) -> Dict[str, Any]:
        return {
            "slack_webhook": self.slack_webhook,
            "slack_bot_token": self.slack_bot_token,
            "slack_channel": self.slack_channel,
            "enabled": bool(self.slack_webhook),  # webhookが設定されていれば有効とみなす
        }

    def get_trade_config(self) -> Dict[str, Any]:
        return {
            "risk_per_trade": self.risk_per_trade,
            "max_loss_percent": self.max_loss_percent,
        }


# 共通インスタンス
config = Config()
