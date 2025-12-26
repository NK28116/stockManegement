#!/usr/bin/env python3
"""
SignalHistoryテーブルを作成するマイグレーションスクリプト

使用方法:
    python -m python.db.migrate_signal_history
"""

from python.db.database import init_db
from python.utils.logger import get_logger

logger = get_logger("db", "migrate")


def main():
    """
    SignalHistoryテーブルを含むすべてのテーブルを作成する
    """
    try:
        logger.info("データベースマイグレーションを開始します...")
        init_db()
        logger.info("✅ データベースマイグレーションが完了しました")
        print("✅ SignalHistoryテーブルが正常に作成されました")
    except Exception as e:
        logger.error(f"❌ マイグレーション中にエラーが発生しました: {e}", exc_info=True)
        print(f"❌ エラー: {e}")
        raise


if __name__ == "__main__":
    main()
