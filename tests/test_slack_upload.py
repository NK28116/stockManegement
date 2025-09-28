import os
import unittest
from unittest.mock import MagicMock, mock_open, patch

from dotenv import load_dotenv

from python.utils.alert import send_alert
from python.utils.upload_file import Slack

load_dotenv()


class TestSlackUpload(unittest.TestCase):
    def setUp(self):
        self.token = "test_token"
        self.channel_id = "test_channel"
        self.slack = Slack(self.token)

    @patch("requests.get")
    @patch("requests.post")
    @patch("builtins.open", new_callable=mock_open, read_data=b"dummy file content")
    def test_upload_file_and_message_success(self, mock_file_open, mock_post, mock_get):
        # Mock for files.getUploadURLExternal
        mock_get.return_value.json.return_value = {
            "ok": True,
            "upload_url": "http://test.upload.url",
            "file_id": "F12345",
        }
        mock_get.return_value.status_code = 200

        # Mock for file upload (requests.post to upload_url)
        mock_post.side_effect = [
            MagicMock(status_code=200),  # For file upload
            MagicMock(
                json=lambda: {"ok": True, "file": {"id": "F12345"}}, status_code=200
            ),  # For files.completeUploadExternal
        ]

        file_path = "dummy/path/to/file.txt"
        file_name = "file.txt"
        message = "テストメッセージ"

        response = self.slack.upload_file_to_slack(
            channel_id=self.channel_id, message=message, file_name=file_name, file_path=file_path
        )

        self.assertTrue(response["ok"])
        mock_file_open.assert_called_once_with(file_path, "rb")

        # Verify files.getUploadURLExternal call
        mock_get.assert_called_once_with(
            "https://slack.com/api/files.getUploadURLExternal",
            params={"filename": file_name, "length": len(b"dummy file content")},
            headers={"Authorization": f"Bearer {self.token}"},
        )

        # Verify file upload call
        mock_post.call_args_list[0].assert_called_with(
            "http://test.upload.url", headers={"Content-Type": "application/octet-stream"}, data=b"dummy file content"
        )

        # Verify files.completeUploadExternal call
        mock_post.call_args_list[1].assert_called_with(
            "https://slack.com/api/files.completeUploadExternal",
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
            json={
                "channel_id": self.channel_id,
                "files": [{"id": "F12345", "title": file_name}],
                "initial_comment": message,
            },
        )

    @patch("requests.post")
    def test_send_message_only_success(self, mock_post):
        mock_post.return_value.json.return_value = {"ok": True, "ts": "12345.67890"}
        mock_post.return_value.status_code = 200

        message = "メッセージのみのテスト"
        response = self.slack.upload_file_to_slack(channel_id=self.channel_id, message=message)

        self.assertTrue(response["ok"])
        mock_post.assert_called_once_with(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
            json={"channel": self.channel_id, "text": message},
        )

    @patch("builtins.open", new_callable=mock_open)
    def test_file_not_found_error(self, mock_file_open):
        mock_file_open.side_effect = FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            self.slack.upload_file_to_slack(
                channel_id=self.channel_id, file_name="non_existent.txt", file_path="non_existent.txt"
            )

    def test_no_message_and_no_file_error(self):
        with self.assertRaises(ValueError):
            self.slack.upload_file_to_slack(channel_id=self.channel_id)

    @patch("requests.get")
    @patch("requests.post")
    @patch("builtins.open", new_callable=mock_open, read_data=b"dummy file content")
    def test_get_upload_url_failure(self, mock_file_open, mock_post, mock_get):
        mock_get.return_value.json.return_value = {"ok": False, "error": "test_error"}
        mock_get.return_value.status_code = 200

        with self.assertRaisesRegex(Exception, "アップロードURLの取得に失敗しました: test_error"):
            self.slack.upload_file_to_slack(
                channel_id=self.channel_id, message="test", file_name="file.txt", file_path="dummy.txt"
            )

    @patch("requests.get")
    @patch("requests.post")
    @patch("builtins.open", new_callable=mock_open, read_data=b"dummy file content")
    def test_file_upload_failure(self, mock_file_open, mock_post, mock_get):
        mock_get.return_value.json.return_value = {
            "ok": True,
            "upload_url": "http://test.upload.url",
            "file_id": "F12345",
        }
        mock_get.return_value.status_code = 200

        mock_post.return_value.status_code = 500  # Simulate upload failure

        with self.assertRaisesRegex(Exception, "ファイルのアップロードに失敗しました"):
            self.slack.upload_file_to_slack(
                channel_id=self.channel_id, message="test", file_name="file.txt", file_path="dummy.txt"
            )

    @patch("requests.get")
    @patch("requests.post")
    @patch("builtins.open", new_callable=mock_open, read_data=b"dummy file content")
    def test_complete_upload_failure(self, mock_file_open, mock_post, mock_get):
        mock_get.return_value.json.return_value = {
            "ok": True,
            "upload_url": "http://test.upload.url",
            "file_id": "F12345",
        }
        mock_get.return_value.status_code = 200

        mock_post.side_effect = [
            MagicMock(status_code=200),  # For file upload success
            MagicMock(
                json=lambda: {"ok": False, "error": "complete_error"}, status_code=200
            ),  # For completeUploadExternal failure
        ]

        with self.assertRaisesRegex(Exception, "アップロード完了通知に失敗しました: complete_error"):
            self.slack.upload_file_to_slack(
                channel_id=self.channel_id, message="test", file_name="file.txt", file_path="dummy.txt"
            )

    @patch("requests.post")
    def test_chat_post_message_failure(self, mock_post):
        mock_post.return_value.json.return_value = {"ok": False, "error": "chat_error"}
        mock_post.return_value.status_code = 200

        with self.assertRaisesRegex(Exception, "メッセージの送信に失敗しました: chat_error"):
            self.slack.upload_file_to_slack(channel_id=self.channel_id, message="test_message")


# 既存のテスト関数はそのまま残すか、必要に応じて削除・修正してください。
class TestActualSlackUpload(unittest.TestCase):
    def test_single_file_upload_actual(self):
        file_path = "data/practice/charts/demo_7203_T_トヨタ自動車.png"
        file_name = "demo_7203_T_トヨタ自動車.png"
        message = "統合テスト: トヨタ自動車のデモチャートをアップロードします。"
        channel_id = os.environ.get("SLACK_CHANNEL")
        slack_bot_token = os.environ.get("SLACK_BOT_TOKEN")

        if not channel_id or not slack_bot_token:
            self.skipTest(
                "SLACK_CHANNEL または SLACK_BOT_TOKEN が .env ファイルに設定されていません。実際のSlackアップロードテストをスキップします。"
            )
            return

        print(f"\nファイルをSlackにアップロードします: {file_name} from {file_path}")
        success = send_alert(
            message=message,
            level="INFO",
            file_path=file_path,
            file_name=file_name,
            is_test_mode=False,  # 実際のSlackアップロードを実行
        )

        self.assertTrue(success, "実際のファイルアップロードテストが失敗しました。")
        print("ファイルアップロードテスト成功。Slackを確認してください。")


if __name__ == "__main__":
    unittest.main()
