#!/bin/bash
set -euo pipefail

# 毎日、最新のレポートファイルをGCSから取得し、Slackに送信するスクリプト
# send_report.sh {daily|weekly|monthly}

# ========================
# 設定
# ========================

# SlackのIncoming Webhook URL
SLACK_WEBHOOK_URL="https://example.invalid/REDACTED_SLACK_WEBHOOK"

# GCSバケット名
BUCKET="stock-managemet-report-file"

# ========================
# 日付の取得
# ========================
TODAY=$(date +"%Y%m%d")

# 引数チェックとPERIOD設定
REPORT_TYPE=""
PERIOD=""
REPORT_BASE_DIR=""

case "$1" in
  "daily")
    REPORT_TYPE="daily"
    PERIOD="1mo"
    REPORT_BASE_DIR="data/report/daily"
    ;;
  "weekly")
    REPORT_TYPE="weekly"
    PERIOD="3mo"
    REPORT_BASE_DIR="data/report/weekly"
    ;;
  "monthly")
    REPORT_TYPE="monthly"
    PERIOD="6mo"
    REPORT_BASE_DIR="data/report/monthly"
    ;;
  *)
    echo "Usage: $0 {daily|weekly|monthly}"
    exit 1
    ;;
esac

# 最新ファイルを検索（summary, detailed, chartImg, plots, trading_rules）
# summary_report_YYYYMMDD_HHMMSS.txt
# detailed_report_YYYYMMDD_HHMMSS.txt
# trading_rules_YYYYMMDD_HHMMSS.txt
# {CODE}_{NAME}.png (chartImg, plots)

# レポートファイルのパスを構築
SUMMARY_GCS_PATH="gs://$BUCKET/$REPORT_BASE_DIR/summary/summary_report_${TODAY}_*.txt"
DETAILED_GCS_PATH="gs://$BUCKET/$REPORT_BASE_DIR/detailed/detailed_report_${TODAY}_*.txt"
TRADING_RULES_GCS_PATH="gs://$BUCKET/$REPORT_BASE_DIR/trading_rules/trading_rules_${TODAY}_*.txt"
CHART_IMG_GCS_PATH="gs://$BUCKET/data/chartImg/$PERIOD/*.png"
PLOTS_GCS_PATH="gs://$BUCKET/data/plots/$PERIOD/*.png"

# 最新ファイルを取得する関数
get_latest_file() {
  local pattern=$1
  local file=$(gsutil ls "$pattern" 2>/dev/null | sort | tail -n 1)
  if [ -z "$file" ]; then
    echo "Warning: No file found for pattern: $pattern" >&2
  fi
  echo "$file"
}

SUMMARY_FILE=$(get_latest_file "$SUMMARY_GCS_PATH")
DETAILED_FILE=$(get_latest_file "$DETAILED_GCS_PATH")
TRADING_RULES_FILE=""
if [ "$REPORT_TYPE" = "monthly" ]; then
  TRADING_RULES_FILE=$(get_latest_file "$TRADING_RULES_GCS_PATH")
fi
CHART_FILE=$(get_latest_file "$CHART_IMG_GCS_PATH")
PLOT_FILE=$(get_latest_file "$PLOTS_GCS_PATH")


# URL変換（gs:// → https://storage.cloud.google.com/）
# ファイルが存在しない場合は空文字列のままにする
SUMMARY_URL=""
if [ -n "$SUMMARY_FILE" ]; then
  SUMMARY_URL=${SUMMARY_FILE/gs:\/\//https://storage.cloud.google.com/}
fi

DETAILED_URL=""
if [ -n "$DETAILED_FILE" ]; then
  DETAILED_URL=${DETAILED_FILE/gs:\/\//https://storage.cloud.google.com/}
fi

TRADING_RULES_URL=""
if [ -n "$TRADING_RULES_FILE" ]; then
  TRADING_RULES_URL=${TRADING_RULES_FILE/gs:\/\//https://storage.cloud.google.com/}
fi

CHART_URL=""
if [ -n "$CHART_FILE" ]; then
  CHART_URL=${CHART_FILE/gs:\/\//https://storage.cloud.google.com/}
fi

PLOT_URL=""
if [ -n "$PLOT_FILE" ]; then
  PLOT_URL=${PLOT_FILE/gs:\/\//https://storage.cloud.google.com/}
fi


# ========================
# Slack送信メッセージ生成
# ========================
MESSAGE="📊 *本日の ${REPORT_TYPE} Report* (${TODAY})
"

if [ -n "$SUMMARY_URL" ]; then
  MESSAGE+="• Summary: ${SUMMARY_URL}\n"
else
  MESSAGE+="• Summary: N/A\n"
fi

if [ -n "$DETAILED_URL" ]; then
  MESSAGE+="• Detailed: ${DETAILED_URL}\n"
else
  MESSAGE+="• Detailed: N/A\n"
fi

if [ -n "$TRADING_RULES_URL" ]; then
  MESSAGE+="• Trading Rules: ${TRADING_RULES_URL}\n"
fi

if [ -n "$CHART_URL" ]; then
  MESSAGE+="• Chart: ${CHART_URL}\n"
else
  MESSAGE+="• Chart: N/A\n"
fi

if [ -n "$PLOT_URL" ]; then
  MESSAGE+="• Plot: ${PLOT_URL}\n"
else
  MESSAGE+="• Plot: N/A\n"
fi


# ========================
# Slackへ送信
# ========================
curl -s -X POST -H 'Content-type: application/json' \
  --data "{\"text\":\"${MESSAGE}\"}" \
  "$SLACK_WEBHOOK_URL"
