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
        self.db_path = self.root_dir / "python" / "db" / "my_stock.db"
        self.log_dir = self.root_dir / "log"
        self.archive_dir = self.root_dir / "data" / "archive"

        # DB接続設定 (SQLite)
        self.db_options = {
            "timeout": int(os.getenv("DB_TIMEOUT", "30")),
            "check_same_thread": os.getenv("DB_CHECK_SAME_THREAD", "false").lower() == "true",
        }

        # 分析パラメータ
        self.default_period = "1mo"
        self.ma_short = 5
        self.ma_long = 25
        self.volatility_period = 10

        # リスク管理パラメータ
        self.max_loss_percent = 3.0  # ストップロス幅
        self.risk_per_trade = 1.0
        self.take_profit_percent = 8.0  # 利確幅

        # トレーティングルール
        self.stop_loss_percent = 0.05  # 5%ストップロス
        self.take_profit_percent = 0.10  # 10%利確
        self.trailing_stop_percent = 0.03  # 3%トレーリングストップ

        # 監視パラメータ
        self.crash_threshold = -3.0  # 暴落アラート閾値
        self.volatility_threshold = 3.0  # ボラリティ
        self.volume_spike_threshold = 2.0  # 出来高
        self.rsi_overbought_threshold = 70.0  # RSI過買い
        self.rsi_oversold_threshold = 30.0  # RSI過売り
        
        # テクニカル指標パラメータ
        self.macd_fast_period = 12  # MACD短期EMA期間
        self.macd_slow_period = 26  # MACD長期EMA期間
        self.macd_long_period = 26  # MACD計算に必要な最小期間（長期EMAと同じ）
        self.macd_signal_period = 9  # MACDシグナル期間
        self.bollinger_period = 20  # ボリンジャーバンド期間
        self.bollinger_std = 2  # ボリンジャーバンド標準偏差

        # ポートフォリオ分析パラメータ
        self.risk_free_rate = 0.001
        self.default_portfolio_file = self.root_dir / "data" / "my_stock.csv"

        # アラート設定
        self.slack_webhook = os.getenv(
            "SLACK_WEBHOOK", "https://hooks.slack.com/services/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"
        )

        # 証券会社API
        self.XXXX_API_KEY = os.getenv("XXXX_API_KEY", "")
        self.XXXX_API_SECRET = os.getenv("XXXX_API_SECRET", "")
        self.XXXX_API_URL = os.getenv("XXXX_API_URL", "")

    def get_watch_config(self) -> Dict[str, Any]:
        return {
            "crash_threshold": self.crash_threshold,
            "volatility_threshold": self.volatility_threshold,
            "volume_spike_threshold": self.volume_spike_threshold,
        }

    def get_db_config(self) -> Dict[str, Any]:
        return {
            "db_path": str(self.db_path),
            "options": {"timeout": 30, "check_same_thread": False},
        }

    def get_alert_config(self) -> Dict[str, Any]:
        """アラート設定を取得"""
        return {
            "slack_webhook": self.slack_webhook,
            "enabled": bool(self.slack_webhook),
        }

    def get_trade_config(self) -> Dict[str, Any]:
        """取引設定を取得"""
        return {
            "risk_per_trade": self.risk_per_trade,
            "max_loss_percent": self.max_loss_percent,
        }


# どのモジュールからも共通で使えるインスタンス
config = Config()
