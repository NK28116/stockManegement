#!/bin/bash
set -euo pipefail

# 毎日、最新のレポートファイルをGCSから取得し、Slackに送信するスクリプト
# send_report.sh {daily|weekly|monthly}

# ========================
# 設定
# ========================

# SlackのIncoming Webhook URL（環境変数から読み込み）
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:?SLACK_WEBHOOK_URL is required}"
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
CHART_IMG_GCS_PATH="gs://$BUCKET/data/chartImg/$PERIOD/"
PLOTS_GCS_PATH="gs://$BUCKET/data/plots/$PERIOD/"

# 最新ファイルを取得する関数
get_latest_file() {
  local pattern=$1
  local file=$(gsutil ls "$pattern" 2>/dev/null | sort | tail -n 1)
  if [ -z "$file" ]; then
    echo "Warning: No file found for pattern: $pattern" >&2
  fi
  echo "$file"
}

# gs:// → https://storage.cloud.google.com/ に変換する関数
# gs:// → https://storage.cloud.google.com/ に変換 + URLエンコード
to_https_url() {
  local gs_path=$1
  local https_path="${gs_path/gs:\/\//https://storage.cloud.google.com/}"
  # 最初の https:// 部分はエンコードしないように分離
  local prefix="https://storage.cloud.google.com/"
  local path="${https_path#${prefix}}"
  echo "${prefix}$(jq -rn --arg x "$path" '$x|@uri')"
}

SUMMARY_FILE=$(get_latest_file "$SUMMARY_GCS_PATH")
DETAILED_FILE=$(get_latest_file "$DETAILED_GCS_PATH")

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


# ========================
# Chart & Plot ファイル一覧取得
# ========================
CHART_FILES=$(gsutil ls "gs://$BUCKET/data/chartImg/$PERIOD/*.png" 2>/dev/null || true)
PLOT_FILES=$(gsutil ls "gs://$BUCKET/data/plots/$PERIOD/*.png" 2>/dev/null || true)

# 連想配列
declare -A charts
declare -A plots

# Chart → 銘柄キーに登録
while IFS= read -r f; do
  [ -z "$f" ] && continue
  base=$(basename "$f" .png)   # 1949_T_SUMITOMO...
  charts["$base"]="$(to_https_url "$f")"
done <<< "$CHART_FILES"

# Plot → 銘柄キーに登録（1949.T_xxx → 1949_T_xxx に変換）
while IFS= read -r f; do
  [ -z "$f" ] && continue
  base=$(basename "$f" .png)                  # 1949.T_SUMITOMO..._indicators
  base=${base/_indicators/}                   # 1949.T_SUMITOMO...
  base=${base/./_}                            # 1949_T_SUMITOMO...
  plots["$base"]="$(to_https_url "$f")"
done <<< "$PLOT_FILES"

#========================
# Slack送信メッセージ生成
# ========================
MESSAGE="📊 *本日の ${REPORT_TYPE} Report* (${TODAY})

## Report
- Summary: ${SUMMARY_URL:-N/A}
- Detailed: ${DETAILED_URL:-N/A}

## Graph

"

# 銘柄ごとにまとめる
for key in "${!charts[@]}"; do
  MESSAGE+="- ${key}
  "
  if [ -n "${charts[$key]}" ]; then
    MESSAGE+="    - Chart: ${charts[$key]}
    "
  fi
  if [ -n "${plots[$key]}" ]; then
    MESSAGE+="    - Plot: ${plots[$key]}
    -------------------------------------------------------------------
    "
  fi
done

# ========================
# Slackへ送信
# ========================
payload=$(jq -Rs --arg text "$MESSAGE" '{text: $text}' <<<"$MESSAGE")

curl -s -X POST -H 'Content-type: application/json' \
  --data "$payload" \
  "$SLACK_WEBHOOK_URL"
