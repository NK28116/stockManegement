#!/usr/bin/env bash
# Git履歴からの機密情報除去 (PRIDEV-307)
#
# 棚卸し (PRIDEV-304) で確定した除去対象:
#   [パス除去] 本来コミットされるべきでないファイル
#     - render-sa-key.json   : GCP SA鍵
#     - KEY.json             : GCP SA鍵 (旧)
#     - .env                 : Slack bot token / webhook
#     - python/__pycache__/  : Slack Webhook入り .pyc
#   [文字列置換] 現存する正当なファイルの過去版に埋め込まれたシークレット
#     - scripts/send_report.sh, .github/workflows/*, README.md, python/config.py
#       に含まれる Slack webhook / GitHub PAT 等
#       → gitleaks レポートから動的に抽出して ***REMOVED*** に置換
#
# 前提:
#   - ミラーバックアップ取得済みであること (PRIDEV-306)
#   - 漏洩シークレットのローテーション完了 (PRIDEV-305) ※必須ではないが強く推奨
#
# このスクリプトは新規クローン上で書き換えを行うのみで、push はしない。
# force-push (PRIDEV-308) は影響を確認したうえで手動で実行すること:
#   cd <WORK_DIR> && git push --force --mirror git@github.com:NK28116/stockManegement.git
set -euo pipefail

REPO_URL="git@github.com:NK28116/stockManegement.git"
WORK_DIR="${1:-$HOME/Documents/PrivateDevelop/stockManegement-purged}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

if [ -e "$WORK_DIR" ]; then
  echo "ERROR: $WORK_DIR は既に存在します。別のパスを指定してください。" >&2
  exit 1
fi

command -v git-filter-repo >/dev/null || { echo "ERROR: git-filter-repo が必要です (brew install git-filter-repo)" >&2; exit 1; }
command -v gitleaks >/dev/null || { echo "ERROR: gitleaks が必要です (brew install gitleaks)" >&2; exit 1; }

echo "==> 新規クローン: $WORK_DIR"
git clone --mirror "$REPO_URL" "$WORK_DIR"
cd "$WORK_DIR"

echo "==> 浄化前スキャン (置換対象シークレットの抽出)"
gitleaks detect --source . --log-opts="--all" --no-banner \
  --report-path "$TMP_DIR/before.json" || true

python3 - "$TMP_DIR/before.json" "$TMP_DIR/replacements.txt" <<'EOF'
import json, sys
findings = json.load(open(sys.argv[1]))
secrets = {f["Secret"] for f in findings if f.get("Secret")}
with open(sys.argv[2], "w") as out:
    for s in sorted(secrets):
        # filter-repo の literal 置換 (デフォルト) を使用
        out.write(f"{s}==>***REMOVED***\n")
print(f"置換対象: {len(secrets)} 件のシークレット")
EOF

echo "==> filter-repo 実行 (パス除去 + シークレット文字列置換)"
git filter-repo \
  --invert-paths \
  --path render-sa-key.json \
  --path KEY.json \
  --path .env \
  --path python/__pycache__/ \
  --replace-text "$TMP_DIR/replacements.txt"

echo "==> 浄化後の再スキャン (PRIDEV-309 の事前検証)"
if gitleaks detect --source . --log-opts="--all" --no-banner; then
  echo "OK: gitleaks 警告ゼロ"
else
  echo "NG: まだシークレットが残っています。レポートを確認してください。" >&2
  exit 1
fi

echo ""
echo "完了。push はまだ実行されていません。"
echo "内容を確認後、以下で force-push してください (PRIDEV-308):"
echo "  cd $WORK_DIR && git push --force --mirror $REPO_URL"
echo "push 後は全コラボレーターが再クローンする必要があります。"
