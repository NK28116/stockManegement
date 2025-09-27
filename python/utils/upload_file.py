import logging  # loggingモジュールを追加
import os

import requests
from dotenv import load_dotenv
from python.utils.logger import get_logger

load_dotenv()
logger = get_logger("upload_file", category="system")


class Slack:
    def __init__(self, token):
        self.token = token

    def upload_file_to_slack(self, channel_id, message=None, file_name=None, file_path=None):
        """
        Slackにファイルまたはメッセージを投稿する関数
        :param channel_id: 投稿先のチャンネルID
        :param message: メッセージ（任意）
        :param file_name: ファイル名(変数)
        :param file_path: ファイルパス（変数）
        :return: API応答のJSONデータ
        :raises FileNotFoundError: ファイルが見つからない場合
        :raises ValueError: メッセージもファイルも指定されていない場合
        :raises Exception: API呼び出しが失敗した場合
        """
        if file_path:
            # ファイルがある場合
            try:
                with open(file_path, "rb") as f:
                    file_blob = f.read()
            except Exception as e:
                raise FileNotFoundError(f"ファイルが見つかりません: {file_path}") from e

            file_size = len(file_blob)

            # アップロードURL取得
            params = {"filename": file_name, "length": file_size}
            headers = {"Authorization": f"Bearer {self.token}"}
            upload_url_response = requests.get(
                "https://slack.com/api/files.getUploadURLExternal", params=params, headers=headers
            )
            upload_url_json = upload_url_response.json()

            if not upload_url_json.get("ok", False):
                raise Exception(f"アップロードURLの取得に失敗しました: {upload_url_json.get('error')}")

            upload_url = upload_url_json["upload_url"]
            file_id = upload_url_json["file_id"]

            # ファイルをアップロード
            upload_headers = {"Content-Type": "application/octet-stream"}
            upload_response = requests.post(upload_url, headers=upload_headers, data=file_blob)

            if upload_response.status_code != 200:
                raise Exception(f"ファイルのアップロードに失敗しました: {upload_response.text}")

            # アップロード完了通知
            complete_upload_payload = {
                "channel_id": channel_id,
                "files": [{"id": file_id, "title": file_name}],
            }  # SLACK_CHANNELをchannel_idに変更
            if message:
                complete_upload_payload["initial_comment"] = message  # Slack APIは initial_comment というキー

            complete_upload_headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
            complete_upload_response = requests.post(
                "https://slack.com/api/files.completeUploadExternal",
                headers=complete_upload_headers,
                json=complete_upload_payload,
            )
            complete_upload_json = complete_upload_response.json()

            if not complete_upload_json.get("ok", False):
                raise Exception(f"アップロード完了通知に失敗しました: {complete_upload_json.get('error')}")

            print("[アップロード] ファイルのアップロードが完了しました。")
            return complete_upload_json

        else:
            # ファイルがない場合は単純なメッセージ送信
            if message is None:
                raise ValueError("file_path も message も両方Noneです。何も投稿するものがありません。")

            chat_payload = {"channel": channel_id, "text": message}
            chat_headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
            chat_response = requests.post(
                "https://slack.com/api/chat.postMessage", headers=chat_headers, json=chat_payload
            )
            chat_json = chat_response.json()

            if not chat_json.get("ok", False):
                raise Exception(f"メッセージの送信に失敗しました: {chat_json.get('error')}")

            print("[投稿] メッセージの送信が完了しました。")
            return chat_json


def check_file_size(file_path, max_size_mb=50):
    """ファイルサイズを確認し、制限を超えている場合はFalseを返す"""
    max_size_bytes = max_size_mb * 1024 * 1024  # MBからバイトに変換

    try:
        file_size = os.path.getsize(file_path)
        if file_size > max_size_bytes:
            logging.warning(
                f"ファイルサイズが制限を超えています: {file_size / (1024 * 1024):.2f}MB " f"(最大: {max_size_mb}MB)"
            )
            return False
        return True
    except OSError as e:
        logging.error(f"ファイルサイズの確認中にエラーが発生しました: {e}")
        return False


if __name__ == "__main__":
    # 環境変数からトークンを読み込む例
    token = os.environ.get("SLACK_BOT_TOKEN")  # "{SLACK_BOT_TOKEN}"を"SLACK_BOT_TOKEN"に変更

    # テスト用（実際の使用時は上記の環境変数を使用することを推奨）
    # token = "YOUR_SLACK_API_TOKEN"  # ここに自分のトークンを設定
    slack = Slack(token)
    slack.upload_file_to_slack(
        channel_id=os.environ.get("SLACK_CHANNEL"),  # "{SLACK_CHANNEL}"をos.environ.get("SLACK_CHANNEL")に変更
        message="ファイルをアップロードします",
        file_name="",  # 送信するファイル名
        file_path="",  # 保存されたファイルパスに変更
    )
