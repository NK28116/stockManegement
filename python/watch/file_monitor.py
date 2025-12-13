import logging
import subprocess
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from python.config import config

logger = logging.getLogger(__name__)


class MyStockCSVHandler(FileSystemEventHandler):
    """
    my_stock.csvの変更を監視し、サービスを再起動するハンドラ。
    """

    def __init__(self, target_file: Path):
        super().__init__()
        self.target_file = target_file
        logger.info(f"my_stock.csv監視を開始します: {self.target_file}")

    def on_modified(self, event):
        """
        ファイルが変更されたときに呼び出される。
        """
        if not event.is_directory and Path(event.src_path) == self.target_file:
            logger.info(f"my_stock.csvが変更されました: {event.src_path}")
            self.restart_service()

    def restart_service(self):
        """
        Systemdサービスを再起動する。
        """
        command = "sudo systemctl daemon-reload && sudo systemctl restart stock.service"
        logger.info(f"サービス再起動コマンドを実行します: {command}")
        try:
            # shell=Trueはセキュリティリスクがあるが、ここではsudoコマンド実行のため必要
            # 実際の運用では、sudoersの設定で特定のコマンドのみパスワードなしで実行できるようにするなどの対策が必要
            subprocess.run(command, shell=True, check=True)
            logger.info("サービスが正常に再起動されました。")
        except subprocess.CalledProcessError as e:
            logger.error(f"サービス再起動コマンドの実行に失敗しました: {e}")
        except Exception as e:
            logger.error(f"予期せぬエラーが発生しました: {e}")


def start_file_monitor():
    """
    my_stock.csvのファイル監視を開始する。
    """
    path = config.codes_path.parent  # my_stock.csvがあるディレクトリを監視
    target_file = config.codes_path  # 監視対象ファイル

    event_handler = MyStockCSVHandler(target_file)
    observer = Observer()
    observer.schedule(
        event_handler, path, recursive=False
    )  # my_stock.csvがあるディレクトリのみ監視
    observer.start()
    logger.info(
        f"ファイル監視を開始しました。ディレクトリ: {path}, ファイル: {target_file}"
    )

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    start_file_monitor()
