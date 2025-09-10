import requests

from python.config import config
from python.utils.logger import get_logger

logger = get_logger("alert", category="watch")

__all__ = ["AlertManager", "send_alert"]


class AlertManager:
    """アラート管理クラス"""

    def __init__(self):
        self.alert_config = config.get_alert_config()

    def send_alert(self, message: str, level: str = "INFO") -> bool:
        """
        アラートを送信する

        Args:
            message: 送信メッセージ
            level: 重要度レベル

        Returns:
            bool: 送信が成功したかどうか
        """
        if not self.alert_config["enabled"]:
            logger.warning("アラート機能が無効です")
            return False

        success = True

        # Slack通知
        if self.alert_config["slack_webhook"]:
            if not self._send_slack(message, level):
                success = False

        # LINE通知
        if self.alert_config["line_token"]:
            if not self._send_line(message):
                success = False

        return success

    def _send_slack(self, message: str, level: str) -> bool:
        """Slackに通知を送信"""
        try:
            payload = {
                "text": "[{level}] {message}",
                "username": "Stock Management Bot",
            }

            response = requests.post(self.alert_config["slack_webhook"], json=payload, timeout=10)

            if response.status_code == 200:
                logger.info("Slack通知送信成功")
                return True
            else:
                logger.error("Slack通知送信失敗: {response.status_code}")
                return False

        except Exception as e:
            logger.error("Slack通知エラー: {e}")
            return False

    def _send_line(self, message: str) -> bool:
        """LINEに通知を送信"""
        try:
            headers = {"Authorization": "Bearer {self.alert_config['line_token']}"}
            data = {"message": message}

            response = requests.post(
                "https://notify-api.line.me/api/notify",
                headers=headers,
                data=data,
                timeout=10,
            )

            if response.status_code == 200:
                logger.info("LINE通知送信成功")
                return True
            else:
                logger.error("LINE通知送信失敗: {response.status_code}")
                return False

        except Exception as e:
            logger.error("LINE通知エラー: {e}")
            return False


# グローバルアラートマネージャー
alert_manager = AlertManager()


def send_alert(message: str, level: str = "INFO") -> bool:
    """アラート送信の簡易関数"""
    return alert_manager.send_alert(message, level)
