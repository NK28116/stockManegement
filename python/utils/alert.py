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
                # ファイルを添付して送信する場合 (files.getUploadURLExternal & files.completeUploadExternal APIを使用)
                slack_token = self.alert_config.get("slack_bot_token")
                slack_channel = self.alert_config.get("slack_channel")
                if not slack_token or not slack_channel:
                    logger.error(
                        "Slack Bot Token または Slack Channel が設定されていません。ファイルを送信できません。"
                    )
                    return False

                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)

                # 1. files.getUploadURLExternal を呼び出してアップロードURLを取得
                get_upload_url = "https://slack.com/api/files.getUploadURLExternal"
                get_upload_headers = {"Authorization": f"Bearer {slack_token}"}
                get_upload_data = {
                    "filename": file_name,
                    "length": file_size,
                }
                get_upload_response = requests.post(
                    get_upload_url, headers=get_upload_headers, data=get_upload_data, timeout=10
                )
                get_upload_json = get_upload_response.json()

                if not get_upload_json.get("ok"):
                    logger.error(f"SlackファイルアップロードURL取得失敗: {get_upload_json.get('error')}")
                    return False

                upload_url = get_upload_json["upload_url"]
                file_id = get_upload_json["file_id"]

                # 2. 取得したURLにファイルを直接アップロード (HTTP PUTリクエスト)
                with open(file_path, "rb") as f:
                    put_response = requests.put(upload_url, data=f, timeout=60)

                if not put_response.ok:
                    logger.error(
                        f"Slackファイルアップロード失敗 (PUT): {put_response.status_code} - {put_response.text}"
                    )
                    return False

                # 3. files.completeUploadExternal を呼び出してアップロード完了を通知
                complete_upload_url = "https://slack.com/api/files.completeUploadExternal"
                complete_upload_headers = {
                    "Authorization": f"Bearer {slack_token}",
                    "Content-Type": "application/json",
                }  # Content-Typeを追加
                complete_upload_payload = {  # dataではなくjsonパラメータを使用
                    "files": [{"id": file_id, "title": file_name}],  # json.dumpsを削除
                    "channel_id": slack_channel,
                    "initial_comment": f"[{level}] {message}",
                }
                complete_upload_response = requests.post(
                    complete_upload_url,
                    headers=complete_upload_headers,
                    json=complete_upload_payload,
                    timeout=10,  # dataをjsonに変更
                )
                complete_upload_json = complete_upload_response.json()

                if complete_upload_json.get("ok"):
                    logger.info(f"Slackにファイル '{file_name}' を送信成功")
                    return True
                else:
                    logger.error(f"Slackにファイル '{file_name}' 送信失敗: {complete_upload_json.get('error')}")
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
