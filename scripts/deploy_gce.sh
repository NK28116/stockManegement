#!/bin/bash
# ===================================================================
# GCE 上のリポジトリを origin/main に更新する (Deploy to GCE ワークフローから実行)
#
#   gcloud compute ssh ... --command "sudo -u <アプリのユーザー> bash -s -- <APP_DIR>" < scripts/deploy_gce.sh
#
# 標準入力で渡されて GCE 上で動くため、このファイル単体で完結させる。
# 手動で実行する場合 (GCE 上で):
#   sudo -u <アプリのユーザー> bash scripts/deploy_gce.sh /home/<アプリのユーザー>/stockManegement
# ===================================================================
set -euo pipefail

APP_DIR="${1:?使い方: deploy_gce.sh <APP_DIR>}"
cd "$APP_DIR"

# v1.1 以降、バケット名はリポジトリに書かず .env から読む。
# 未設定のまま更新すると日次バッチが止まるため、ここで中止する (旧コードのまま動き続ける)。
if ! grep -qE '^GCS_BUCKET_NAME=.+' .env 2>/dev/null; then
    echo "ERROR: .env に GCS_BUCKET_NAME がありません。設定してから再実行してください。" >&2
    exit 1
fi

# 個人データ (保有株 CSV など) は v1.1 で Git の管理対象から外した。
# まだ管理下にある古いチェックアウトでも pull で消えたり止まったりしないよう、
# 退避 → 管理下の版へ戻す → pull → 退避した版を書き戻す、の順で更新する。
# 一度 v1.1 を取り込めば対象は無くなり、以降は何もしない。
PRIVATE_FILES="data/my_stock.csv data/my_stock_local.csv data/latest_indicators.json stock_db.dump cloud-sql-proxy"
BACKUP_DIR="$HOME/stock-private-backup/$(date +%Y%m%d%H%M%S)"
for f in $PRIVATE_FILES; do
    if [ -e "$f" ] && git ls-files --error-unmatch "$f" >/dev/null 2>&1; then
        mkdir -p "$BACKUP_DIR/$(dirname "$f")"
        cp -p "$f" "$BACKUP_DIR/$f"
        git checkout -- "$f"
        echo "退避しました: $f -> $BACKUP_DIR/$f"
    fi
done

BEFORE="$(git rev-parse --short HEAD)"
# fast-forward できない (サーバー上でコミットされている等) 場合は止める
git pull --ff-only origin main
AFTER="$(git rev-parse --short HEAD)"

for f in $PRIVATE_FILES; do
    if [ -e "$BACKUP_DIR/$f" ] && [ ! -e "$f" ]; then
        mkdir -p "$(dirname "$f")"
        cp -p "$BACKUP_DIR/$f" "$f"
    fi
done

# 依存パッケージを requirements.txt (バージョン固定) に合わせる
./venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements.txt

echo "デプロイ完了: $BEFORE -> $AFTER"
