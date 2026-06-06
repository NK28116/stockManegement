#!/bin/bash
# ===================================================================
# 日次バッチ（GCEワーカー用）
#   1) 全銘柄チャート生成（ローカル）
#   2) GCSへ同期（charts/signals, charts/indicators を更新）
#   3) シグナル分析（signals テーブルへ保存）
# cron から呼び出す。ログは log/cron_daily.log に追記。
# 環境変数（DB/GCS等）は python-dotenv が .env から読み込む。
# ===================================================================
set -uo pipefail

PROJECT_ROOT="/home/niwa_kazuhiro/stockManegement"
cd "$PROJECT_ROOT" || exit 1

# shellcheck disable=SC1091
source venv/bin/activate

mkdir -p log
LOG="$PROJECT_ROOT/log/cron_daily.log"

{
    echo "==================== $(date '+%Y-%m-%d %H:%M:%S') cron_daily START ===================="

    echo "[1/3] generate charts (1mo)"
    python -m python.visualization.generate_all_charts 1mo

    echo "[2/3] sync charts to GCS"
    python scripts/sync_data_to_gcs.py 1mo

    echo "[3/3] analyze signals"
    python python/watch/analyze.py

    echo "==================== $(date '+%Y-%m-%d %H:%M:%S') cron_daily DONE ===================="
} >> "$LOG" 2>&1
