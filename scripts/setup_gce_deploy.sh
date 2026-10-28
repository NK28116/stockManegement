#!/bin/bash
# ===================================================================
# GitHub Actions から GCE へ自動デプロイするための GCP 側の設定 (1 回だけ実行)
#
#   GCE_INSTANCE=<インスタンス名> GCE_ZONE=<ゾーン> bash scripts/setup_gce_deploy.sh
#
# 何度実行しても同じ結果になる (既にある設定はそのまま)。
# 手順と仕組みは Docs/DEPLOY_GCE.md を参照。
#
# 作るもの:
#   - デプロイ専用のサービスアカウント (既定: gce-deployer)
#   - 権限 (必要な範囲だけ)
#       * プロジェクト: IAP トンネルの利用 / インスタンス情報の参照
#       * 対象インスタンスのみ: OS Login (sudo あり)
#       * VM に付いているサービスアカウント: その SA として動く VM へのログインに必要
#   - GitHub リポジトリからこの SA を使えるようにする Workload Identity の紐付け
#     (プール・プロバイダーは scripts/setup_wif.sh で作ったものを使う)
# ===================================================================
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
GCE_INSTANCE="${GCE_INSTANCE:?GCE_INSTANCE にインスタンス名を指定してください}"
GCE_ZONE="${GCE_ZONE:?GCE_ZONE にゾーンを指定してください}"
SA_NAME="${SA_NAME:-gce-deployer}"
POOL_NAME="${POOL_NAME:-github-actions-pool-1}"
PROVIDER_NAME="${PROVIDER_NAME:-github-actions-provider-1}"

if [ -z "$PROJECT_ID" ]; then
    echo "ERROR: PROJECT_ID を指定するか、gcloud config set project で設定してください。" >&2
    exit 1
fi

# GitHub リポジトリ (owner/repo) を git remote から求める
if [ -z "${GITHUB_REPO:-}" ]; then
    REMOTE_URL="$(git config --get remote.origin.url)"
    if [[ "$REMOTE_URL" =~ github\.com[:/]([^/]+)/([^/]+)$ ]]; then
        GITHUB_REPO="${BASH_REMATCH[1]}/${BASH_REMATCH[2]%.git}"
    else
        echo "ERROR: GitHub リポジトリを判別できません。GITHUB_REPO=<owner>/<repo> を指定してください。" >&2
        exit 1
    fi
fi

SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "プロジェクト:   $PROJECT_ID"
echo "インスタンス:   $GCE_INSTANCE ($GCE_ZONE)"
echo "リポジトリ:     $GITHUB_REPO"
echo "デプロイ用 SA:  $SA_EMAIL"
echo "------------------------------------------------"

# 1. デプロイ専用のサービスアカウント
if gcloud iam service-accounts describe "$SA_EMAIL" --project "$PROJECT_ID" >/dev/null 2>&1; then
    echo "サービスアカウントは作成済みです。"
else
    gcloud iam service-accounts create "$SA_NAME" --project "$PROJECT_ID" \
        --display-name "GitHub Actions GCE deployer"
fi

# 2. 権限
# IAP 経由の SSH トンネル
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member "serviceAccount:$SA_EMAIL" --role roles/iap.tunnelResourceAccessor \
    --condition None >/dev/null
# gcloud compute ssh がインスタンスの情報を読むため
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member "serviceAccount:$SA_EMAIL" --role roles/compute.viewer \
    --condition None >/dev/null
# OS Login (sudo あり) は対象インスタンスだけに付ける。
# アプリのユーザー (リポジトリの持ち主) として実行するために sudo -u が要る。
gcloud compute instances add-iam-policy-binding "$GCE_INSTANCE" \
    --project "$PROJECT_ID" --zone "$GCE_ZONE" \
    --member "serviceAccount:$SA_EMAIL" --role roles/compute.osAdminLogin >/dev/null

# VM にサービスアカウントが付いている場合、OS Login でのログインにはその SA の利用権限が要る
VM_SA="$(gcloud compute instances describe "$GCE_INSTANCE" --project "$PROJECT_ID" --zone "$GCE_ZONE" \
    --format 'value(serviceAccounts[0].email)')"
if [ -n "$VM_SA" ]; then
    gcloud iam service-accounts add-iam-policy-binding "$VM_SA" --project "$PROJECT_ID" \
        --member "serviceAccount:$SA_EMAIL" --role roles/iam.serviceAccountUser >/dev/null
    echo "VM のサービスアカウント $VM_SA の利用権限を付けました。"
fi

# 3. GitHub リポジトリからこの SA を使えるようにする
POOL_ID="$(gcloud iam workload-identity-pools describe "$POOL_NAME" --project "$PROJECT_ID" \
    --location global --format 'value(name)')"
PROVIDER_ID="$(gcloud iam workload-identity-pools providers describe "$PROVIDER_NAME" --project "$PROJECT_ID" \
    --location global --workload-identity-pool "$POOL_NAME" --format 'value(name)')"
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" --project "$PROJECT_ID" \
    --role roles/iam.workloadIdentityUser \
    --member "principalSet://iam.googleapis.com/${POOL_ID}/attribute.repository/${GITHUB_REPO}" >/dev/null

# 4. 確認 (変更はしない)
OSLOGIN="$(gcloud compute instances describe "$GCE_INSTANCE" --project "$PROJECT_ID" --zone "$GCE_ZONE" \
    --format 'value(metadata.items.enable-oslogin)')"
if [ -z "$OSLOGIN" ]; then
    OSLOGIN="$(gcloud compute project-info describe --project "$PROJECT_ID" \
        --format 'value(commonInstanceMetadata.items.enable-oslogin)')"
fi
if [ "${OSLOGIN^^}" != "TRUE" ]; then
    echo "WARNING: OS Login が有効になっていません (enable-oslogin=${OSLOGIN:-未設定})。" >&2
fi
IAP_RULES="$(gcloud compute firewall-rules list --project "$PROJECT_ID" \
    --filter 'direction=INGRESS AND sourceRanges:35.235.240.0/20 AND disabled=false' --format 'value(name)')"
if [ -z "$IAP_RULES" ]; then
    echo "WARNING: IAP (35.235.240.0/20) から tcp:22 を許可するファイアウォールルールが見つかりません。" >&2
fi

echo ""
echo "===================================================="
echo "完了しました。GitHub の Settings → Secrets and variables → Actions に登録してください。"
echo ""
echo "公開リポジトリの Actions のログは誰でも読めるため、識別子もすべて Secrets に入れる (ログでは *** になる)。"
echo ""
echo "  GCP_WIF_PROVIDER             ${PROVIDER_ID}   (Cloud Run 用に登録済みなら不要)"
echo "  GCE_DEPLOY_SERVICE_ACCOUNT   ${SA_EMAIL}"
echo "  GCE_INSTANCE                 ${GCE_INSTANCE}"
echo "  GCE_ZONE                     ${GCE_ZONE}"
echo "  GCE_USERNAME                 <リポジトリの持ち主のユーザー名> (登録済みなら不要)"
echo "===================================================="
