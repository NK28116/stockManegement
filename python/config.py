"""
設定ファイル
環境変数やパラメータを管理
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any


class Config:
    """設定管理クラス"""

    def __init__(self):
        # ルートディレクトリ
        self.root_dir = Path(__file__).resolve().parent.parent

        # ファイル・ディレクトリパス
        self.codes_path = os.getenv("CODES_PATH", str(self.root_dir / "data" / "my_stock.csv"))
        self.output_dir = os.getenv("OUTPUT_DIR", str(self.root_dir / "data"))
        self.db_path = os.getenv("DB_PATH", str(self.root_dir /"python"/"db" / "stock.db"))
        self.log_dir = os.getenv("LOG_DIR", str(self.root_dir / "logs"))
        self.trading_rules = os.getenv("TRADING_RULES", str(self.root_dir /"trading" /"trading_rules.py"))
        self.archive_dir = os.getenv("ARCHIVE_DIR", str(self.root_dir / "data" / "archive"))

        # DB接続設定 (SQLite)
        self.db_options = {
            "timeout": int(os.getenv("DB_TIMEOUT", "30")),
            "check_same_thread": os.getenv("DB_CHECK_SAME_THREAD", "false").lower() == "true"
        }

        # アラート設定
        self.slack_webhook = os.getenv("SLACK_WEBHOOK", "")
        self.line_token = os.getenv("LINE_TOKEN", "")

        # 分析パラメータ
        self.default_period = os.getenv("DEFAULT_PERIOD", "1mo")
        self.ma_short = int(os.getenv("MA_SHORT", "5"))
        self.ma_long = int(os.getenv("MA_LONG", "25"))


        # リスク管理パラメータ
        self.max_loss_percent = float(os.getenv("MAX_LOSS_PERCENT", "2.0"))
        self.risk_per_trade = float(os.getenv("RISK_PER_TRADE", "1.0"))

        # 監視パラメータ
        self.crash_threshold = float(os.getenv("CRASH_THRESHOLD", "-5.0"))
        self.volatility_threshold = float(os.getenv("VOLATILITY_THRESHOLD", "3.0"))
        self.volume_spike_threshold = float(os.getenv("VOLUME_SPIKE_THRESHOLD", "2.0"))

        # ポートフォリオ分析パラメータ
        self.risk_free_rate = float(os.getenv("RISK_FREE_RATE", "0.001"))
        self.default_portfolio_file = os.getenv("PORTFOLIO_FILE", str(self.root_dir / "data" / "portfolio.csv"))

    def get_alert_config(self) -> Dict[str, Any]:
        """アラート設定を取得"""
        return {
            "slack_webhook": self.slack_webhook,
            "line_token": self.line_token,
            "enabled": bool(self.slack_webhook or self.line_token)
        }

    def get_watch_config(self) -> Dict[str, Any]:
        """監視設定を取得"""
        return {
            "crash_threshold": self.crash_threshold,
            "volatility_threshold": self.volatility_threshold,
            "volume_spike_threshold": self.volume_spike_threshold,
        }

    def get_db_config(self) -> Dict[str, Any]:
        """DB接続設定を取得"""
        return {
            "db_path": self.db_path,
            "options": self.db_options
        }


# モジュールレベルでConfigインスタンスを作成
config = Config()
sys.modules[__name__].config = config
