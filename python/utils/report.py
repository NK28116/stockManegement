import os
from datetime import datetime

from python.config import config
from python.utils.alert import send_alert
from python.utils.logger import get_logger

logger = get_logger("report", category="report")

__all__ = ["send_daily_report", "send_weekly_report", "send_monthly_report"]


def _get_latest_report_file(report_type: str) -> str | None:
    """指定された種類の最新レポートファイルパスを取得する"""
    report_dir = config.root_dir / "data" / "report" / report_type
    if not report_dir.exists():
        return None

    # ファイル名パターン: summary_report_YYYYMMDD_HHMMSS.txt または detailed_report_YYYYMMDD_HHMMSS.txt
    files = sorted(report_dir.glob(f"{report_type}_report_*.txt"), reverse=True)
    return str(files[0]) if files else None


def send_daily_report():
    """日次レポートをSlackに送信する"""
    logger.info("日次レポートを生成し、Slackに送信します。")

    # 例: 日足データ分析の概要
    message = f"【日次レポート】 {datetime.now().strftime('%Y-%m-%d')}\n\n"
    message += "今日の市場の動きの概要や、日足での急落アラートなどをここに含めます。\n"
    message += "詳細な日足分析結果はログまたは別途生成されるレポートをご確認ください。"

    send_alert(message, level="INFO")
    logger.info("日次レポートのSlack送信が完了しました。")


def send_weekly_report():
    """週次レポートをSlackに送信する"""
    logger.info("週次レポートを生成し、Slackに送信します。")

    message = f"【週次レポート】 {datetime.now().strftime('%Y-%m-%d')} 週次分析\n\n"

    # ポートフォリオ分析サマリーレポートの取得
    summary_report_path = _get_latest_report_file("summary")
    if summary_report_path and os.path.exists(summary_report_path):
        with open(summary_report_path, "r", encoding="utf-8") as f:
            summary_content = f.read()
            # サマリーレポートの主要部分を抽出してメッセージに含める
            message += "【ポートフォリオサマリー】\n"
            # 例: 総投資額、総リターン、年率リターンなどを抽出
            for line in summary_content.splitlines():
                if "総投資額" in line or "総リターン" in line or "年率リターン" in line or "シャープレシオ" in line:
                    message += f"{line}\n"
            message += f"\n詳細レポート: file://{summary_report_path}\n"
    else:
        message += "ポートフォリオサマリーレポートが見つかりませんでした。\n"

    # グラフ画像へのリンク（例）
    plot_dir = config.root_dir / "data" / "plots"
    if plot_dir.exists():
        image_files = sorted(plot_dir.glob("*.png"), reverse=True)
        if image_files:
            message += "\n【最新のチャート画像】\n"
            for img_file in image_files[:3]:  # 最新の3枚を例として
                message += f"- file://{img_file}\n"
        else:
            message += "最新のチャート画像が見つかりませんでした。\n"

    send_alert(message, level="INFO")
    logger.info("週次レポートのSlack送信が完了しました。")


def send_monthly_report():
    """月次レポートをSlackに送信する"""
    logger.info("月次レポートを生成し、Slackに送信します。")

    message = f"【月次レポート】 {datetime.now().strftime('%Y-%m-%d')} 月次評価\n\n"

    # 詳細レポートへのリンク
    detailed_report_path = _get_latest_report_file("detailed")
    if detailed_report_path and os.path.exists(detailed_report_path):
        message += "【詳細レポート】\n"
        message += f"file://{detailed_report_path}\n"
    else:
        message += "詳細レポートが見つかりませんでした。\n"

    message += "\n今月のポートフォリオパフォーマンスや再構築検討事項などをここに含めます。"

    send_alert(message, level="INFO")
    logger.info("月次レポートのSlack送信が完了しました。")


if __name__ == "__main__":
    # テスト実行
    print("--- 日次レポートテスト ---")
    send_daily_report()
    print("\n--- 週次レポートテスト ---")
    send_weekly_report()
    print("\n--- 月次レポートテスト ---")
    send_monthly_report()
