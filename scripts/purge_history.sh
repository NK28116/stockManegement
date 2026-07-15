#!/usr/bin/env bash
# Git履歴からの機密情報除去 (PRIDEV-307)
#
# 棚卸し (PRIDEV-304) で確定した除去対象:
#   - render-sa-key.json                 : GCP SA鍵 (commit e7149e5)
#   - python/__pycache__/                : Slack Webhook入り .pyc (commits 59f94d9, abfec03 ほか)
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

if [ -e "$WORK_DIR" ]; then
  echo "ERROR: $WORK_DIR は既に存在します。別のパスを指定してください。" >&2
  exit 1
fi

command -v git-filter-repo >/dev/null || { echo "ERROR: git-filter-repo が必要です (brew install git-filter-repo)" >&2; exit 1; }

echo "==> 新規クローン: $WORK_DIR"
git clone --mirror "$REPO_URL" "$WORK_DIR"
cd "$WORK_DIR"

echo "==> filter-repo 実行 (対象パスを全履歴から除去)"
git filter-repo \
  --invert-paths \
  --path render-sa-key.json \
  --path python/__pycache__/

echo "==> 除去結果の確認"
for p in render-sa-key.json "python/__pycache__/config.cpython-313.pyc"; do
  if git log --all --oneline -- "$p" | grep -q .; then
    echo "NG: $p がまだ履歴に残っています" >&2
    exit 1
  fi
  echo "OK: $p は履歴から除去されました"
done

echo ""
echo "完了。push はまだ実行されていません。"
echo "内容を確認後、以下で force-push してください (PRIDEV-308):"
echo "  cd $WORK_DIR && git push --force --mirror $REPO_URL"
echo "push 後は全コラボレーターが再クローンする必要があります。"
