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
        self, message: str, level: str = "INFO", file_path: str | None = None, is_test_mode: bool = False
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
                return self._send_slack(message, level, file_path)

        if not self.alert_config["enabled"]:
            logger.warning("アラート機能が無効です")
            return False

        # Slack通知
        if self.alert_config["slack_webhook"]:
            return self._send_slack(message, level, file_path)
        return False  # Slack webhookが設定されていない場合

    def _send_slack(self, message: str, level: str, file_path: str | None = None) -> bool:
        """Slackに通知を送信"""
        try:
            if file_path and os.path.exists(file_path):
                # ファイルを添付して送信する場合 (files.upload APIを使用)
                # Slack Bot Token (xoxb-...) が必要
                slack_token = self.alert_config.get("slack_bot_token")
                if not slack_token:
                    logger.error("Slack Bot Token が設定されていません。ファイルを送信できません。")
                    return False

                # ファイル名を取得
                file_name = os.path.basename(file_path)

                # files.upload API のエンドポイント
                upload_url = "https://slack.com/api/files.upload"
                headers = {"Authorization": f"Bearer {slack_token}"}
                data = {
                    "channels": self.alert_config["slack_channel"],  # 送信先のチャンネルID
                    "initial_comment": f"[{level}] {message}",
                    "title": file_name,
                }
                with open(file_path, "rb") as f:
                    files = {"file": (file_name, f, "application/octet-stream")}
                    response = requests.post(upload_url, headers=headers, data=data, files=files, timeout=30)

                if response.status_code == 200 and response.json().get("ok"):
                    logger.info(f"Slackにファイル '{file_name}' を送信成功")
                    return True
                else:
                    logger.error(f"Slackにファイル '{file_name}' 送信失敗: {response.status_code} - {response.text}")
                    return False
            else:
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


def send_alert(message: str, level: str = "INFO", file_path: str | None = None, is_test_mode: bool = False) -> bool:
    """アラート送信の簡易関数"""
    return alert_manager.send_alert(message, level, file_path, is_test_mode)
