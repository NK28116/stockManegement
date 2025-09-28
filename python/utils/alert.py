import os

import requests

from python.config import config
from python.utils.logger import get_logger

logger = get_logger("alert", category="watch")

__all__ = ["AlertManager", "send_alert"]


class AlertManager:
    """アラート管理クラス"""

    def __init__(self):
        self.alert_config = config.get_alert_config()

    def send_alert(
        self,
        message: str,
        level: str = "INFO",
        is_test_mode: bool = False,
    ) -> bool:
        """
        アラートを送信する

        Args:
            message: 送信メッセージ
            level: 重要度レベル
            is_test_mode: テストモードかどうか

        Returns:
            bool: 送信が成功したかどうか
        """
        if is_test_mode:
            logger.info("TEST - slackメッセージのみ送信します")
            if not self.alert_config["slack_webhook"]:
                logger.warning("slack WEBHOOK が設定されていません")
                return True  # テストモードなので成功として扱う
            else:
                # SLACK_WEBHOOKが設定されている場合、テストモードでも実際にSlack通知を送信
                return self._send_slack(message, level)

        if not self.alert_config["enabled"]:
            logger.warning("アラート機能が無効です")
            return False

        # Slack通知
        if self.alert_config["slack_webhook"]:
            return self._send_slack(message, level)
        return False  # Slack webhookが設定されていない場合

    def _send_slack(
        self, message: str, level: str
    ) -> bool:
        """Slackに通知を送信"""
        try:
            # テキストメッセージのみ送信する場合 (Incoming Webhookを使用)
            payload = {
                "text": f"[{level}] {message}",
                "username": "Stock Management Bot",
            }
            response = requests.post(self.alert_config["slack_webhook"], json=payload, timeout=10)

            if response.status_code == 200:
                logger.info("Slack通知送信成功")
                return True
            else:
                logger.error(f"Slack通知送信失敗: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Slack通知エラー: {e}")
            return False


# グローバルアラートマネージャー
alert_manager = AlertManager()


def send_alert(
    message: str,
    level: str = "INFO",
    is_test_mode: bool = False,
) -> bool:
    """アラート送信の簡易関数"""
    return alert_manager.send_alert(message, level, is_test_mode)
