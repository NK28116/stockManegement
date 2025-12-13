import os

import requests
from dotenv import load_dotenv

from python.utils.logger import get_logger

load_dotenv()
logger = get_logger("upload_file", category="system")


class Slack:
    def __init__(self, token):
        self.token = token

    def send_message_to_slack(self, channel_id, message: str):
        """
        Slackにメッセージを投稿する関数
        :param channel_id: 投稿先のチャンネルID
        :param message: 送信するメッセージ
        :return: API応答のJSONデータ
        :raises ValueError: メッセージが指定されていない場合
        :raises Exception: API呼び出しが失敗した場合
        """
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
    token = os.environ.get("SLACK_BOT_TOKEN")
    slack = Slack(token)
    slack.send_message_to_slack(
        channel_id=os.environ.get("SLACK_CHANNEL"),
        message="テストメッセージを送信します。",
    )
