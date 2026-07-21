#!/bin/bash
# scripts/setup_iam.sh
# IAM 最小権限セットアップ (PRIDEV-111)
#
# 設計方針（最小権限の原則）:
#   - render-web-ui SA (Render の Web UI):
#       GCS バケット単位の objectAdmin のみ。プロジェクトレベル権限は付与しない。
#   - GCE ワーカー (Compute default SA):
#       cron_daily.sh が必要とするのは GCS 読み書きと Cloud Logging 書き込みのみ。
#       既定で付与されがちな roles/editor は使用しない（削除手順は下部コメント参照）。
#   - Secret Manager: Slack が MVP 範囲外となったため accessor は付与しない。
#     （必要になった時点でこのスクリプトに追記して再実行する）
#
# 冪等: add-iam-policy-binding / gcloud storage buckets add-iam-policy-binding は
#       既存バインディングがあっても安全に再実行できる。

set -euo pipefail

PROJECT_ID="${PROJECT_ID:?PROJECT_ID is required (e.g. export PROJECT_ID=stockmanagement-494305)}"
BUCKET_NAME="${BUCKET_NAME:?BUCKET_NAME is required (e.g. export BUCKET_NAME=stock-management-494305-prod)}"
WEB_SA_NAME="${SERVICE_ACCOUNT_NAME:-render-web-ui}"

WEB_SA="${WEB_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
GCE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "== IAM setup for project: $PROJECT_ID =="
echo "   Web UI SA : $WEB_SA"
echo "   GCE SA    : $GCE_SA"
echo "   Bucket    : gs://$BUCKET_NAME"

# 1. Web UI (Render) -> バケット単位の GCS 読み書きのみ
echo "-- Grant objectAdmin on bucket to $WEB_SA"
gcloud storage buckets add-iam-policy-binding "gs://$BUCKET_NAME" \
    --member="serviceAccount:$WEB_SA" \
    --role="roles/storage.objectAdmin" \
    --condition=None >/dev/null

# 2. GCE ワーカー -> バケット単位の GCS 読み書き + Cloud Logging 書き込み
echo "-- Grant objectAdmin on bucket to $GCE_SA"
gcloud storage buckets add-iam-policy-binding "gs://$BUCKET_NAME" \
    --member="serviceAccount:$GCE_SA" \
    --role="roles/storage.objectAdmin" \
    --condition=None >/dev/null

echo "-- Grant logging.logWriter (project) to $GCE_SA"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$GCE_SA" \
    --role="roles/logging.logWriter" \
    --condition=None >/dev/null

echo "== setup complete =="
echo ""
echo "広範囲権限の削除（バケット単位付与の動作確認後に実行すること）:"
echo "  # render-web-ui のプロジェクトレベル objectAdmin を削除"
echo "  gcloud projects remove-iam-policy-binding $PROJECT_ID \\"
echo "      --member=serviceAccount:$WEB_SA --role=roles/storage.objectAdmin"
echo "  # GCE default SA の editor を削除"
echo "  gcloud projects remove-iam-policy-binding $PROJECT_ID \\"
echo "      --member=serviceAccount:$GCE_SA --role=roles/editor"
