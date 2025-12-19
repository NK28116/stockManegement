import os

import requests
from dotenv import load_dotenv

from python.utils.logger import get_logger
from python.utils.secret_manager import get_secret

load_dotenv()
logger = get_logger("upload_file", category="system")


class Slack:
    def __init__(self, token=None):
        """
        Slackクライアントを初期化する。
        tokenが指定されていない場合、環境変数 SLACK_BOT_TOKEN、
        次に Secret Manager からの取得を試みる。
        """
        self.token = token

        if not self.token:
            self.token = os.environ.get("SLACK_BOT_TOKEN")

        if not self.token:
            self.token = get_secret("SLACK_BOT_TOKEN")

        if not self.token:
            logger.warning("Slack token could not be found in args, env vars, or Secret Manager.")

    def send_message_to_slack(self, channel_id, message: str):
        """
        Slackにメッセージを投稿する関数
        :param channel_id: 投稿先のチャンネルID
        :param message: 送信するメッセージ
        :return: API応答のJSONデータ
        :raises ValueError: メッセージが指定されていない場合
        :raises Exception: API呼び出しが失敗した場合
        """
        if not self.token:
            logger.error("Slack token is not configured.")
            return {"ok": False, "error": "token_not_configured"}

        if message is None or not message.strip():
            raise ValueError("メッセージが指定されていません。")

        chat_payload = {"channel": channel_id, "text": message}
        chat_headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        chat_response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers=chat_headers,
            json=chat_payload,
        )
        chat_json = chat_response.json()

        if not chat_json.get("ok", False):
            raise Exception(f"メッセージの送信に失敗しました: {chat_json.get('error')}")

        print("[投稿] メッセージの送信が完了しました。")
        return chat_json


if __name__ == "__main__":
    slack = Slack()
    slack.send_message_to_slack(
        channel_id=os.environ.get("SLACK_CHANNEL"),
        message="テストメッセージを送信します。",
    )
