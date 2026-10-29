#!/bin/bash
# ===================================================================
# ローカルで Web UI を起動する (make dev)
#
#   make dev                  # 空いているポート (8888 から) で起動
#   DEV_PORT=9000 make dev    # ポートを指定
#   make dev-reset            # ローカルのデータをサンプルで作り直してから起動
#
# develop、そこから切ったブランチ、git worktree のどこで実行しても、
# 「そのチェックアウトのコード」と「そのチェックアウト専用のローカルデータ」で動く。
# 本番のデータや通知には触れない:
#   - GCS は使わない (data/my_stock_local.csv とローカルのチャートを読む)
#   - DB は SQLite (data/dev/dev.db)。PostgreSQL や Secret Manager に接続しない
#   - Slack へ通知しない、ログイン不要 (APP_ENV=local)
# .env に本番の値が書いてあっても、上の項目はここで上書きする。
# どうしても本番の GCS などにつなぎたいときだけ DEV_USE_CLOUD=1 を付ける (非推奨)。
# 手順: Docs/LOCAL_DEV.md
# ===================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# worktree では、メインのチェックアウトの場所を求める (venv やデータの流用元)
MAIN_ROOT="$(cd "$(git rev-parse --git-common-dir)/.." && pwd)"

# --- Python (venv) -------------------------------------------------
# このチェックアウトの venv → メインのチェックアウトの venv → PATH の python3 の順で使う
PYTHON=""
for candidate in "$ROOT/venv/bin/python" "$MAIN_ROOT/venv/bin/python" "$ROOT/.venv/bin/python" "$MAIN_ROOT/.venv/bin/python"; do
    if [ -x "$candidate" ]; then
        PYTHON="$candidate"
        break
    fi
done
PYTHON="${PYTHON:-$(command -v python3)}"
if ! "$PYTHON" -c "import uvicorn, fastapi" 2>/dev/null; then
    echo "ERROR: $PYTHON に uvicorn / fastapi がありません。" >&2
    echo "  python3 -m venv venv && ./venv/bin/pip install -r requirements.txt" >&2
    exit 1
fi

# --- ローカル専用の設定 (.env より優先) ----------------------------
# python-dotenv は既に設定されている環境変数を上書きしないため、ここで決めた値が使われる
export APP_ENV=local
export APP_PASSWORD_HASH=""
export AUTH_COOKIE_SECURE=false
export DB_ENV=local
export DB_TYPE=sqlite
export SQLITE_PATH="$ROOT/data/dev/dev.db"
if [ "${DEV_USE_CLOUD:-0}" != "1" ]; then
    export GCS_BUCKET_NAME=""
    export GOOGLE_CLOUD_PROJECT=""
    export GCP_PROJECT_ID=""
    export SLACK_WEBHOOK_URL=""
    export SLACK_WEBHOOK=""
    export SLACK_BOT_TOKEN=""
fi

# --- ローカルデータ ------------------------------------------------
# data/ は Git の管理外なので、新しい worktree では空になる。
# 無ければ、メインのチェックアウトのデータ → サンプルの順で用意する
mkdir -p data/dev
if [ "${DEV_RESET:-0}" = "1" ]; then
    echo "ローカルのデータをサンプルで作り直します"
    rm -f data/my_stock_local.csv "$SQLITE_PATH"
fi
if [ ! -f data/my_stock_local.csv ]; then
    if [ "${DEV_RESET:-0}" != "1" ] && [ "$MAIN_ROOT" != "$ROOT" ] && [ -f "$MAIN_ROOT/data/my_stock_local.csv" ]; then
        cp -p "$MAIN_ROOT/data/my_stock_local.csv" data/my_stock_local.csv
        echo "メインのチェックアウトの data/my_stock_local.csv をコピーしました"
    else
        cp -p data/my_stock.sample.csv data/my_stock_local.csv
        echo "data/my_stock.sample.csv から data/my_stock_local.csv を作りました"
    fi
fi

# チャート画像と指標もメインのチェックアウトから流用する (無ければ「分析待ち」と表示される)
if [ "$MAIN_ROOT" != "$ROOT" ]; then
    for d in data/plots data/chartImg; do
        if [ ! -d "$d" ] && [ -d "$MAIN_ROOT/$d" ]; then
            mkdir -p "$(dirname "$d")"
            cp -Rp "$MAIN_ROOT/$d" "$d"
        fi
    done
    if [ ! -f data/latest_indicators.json ] && [ -f "$MAIN_ROOT/data/latest_indicators.json" ]; then
        cp -p "$MAIN_ROOT/data/latest_indicators.json" data/latest_indicators.json
    fi
fi

# --- ポート ----------------------------------------------------------
# 複数の worktree を同時に起動できるよう、使用中なら次の番号を使う
PORT="${DEV_PORT:-8888}"
while "$PYTHON" - "$PORT" <<'EOF' 2>/dev/null; do
import socket, sys
s = socket.socket()
try:
    s.bind(("127.0.0.1", int(sys.argv[1])))
except OSError:
    sys.exit(0)  # 使用中
sys.exit(1)
EOF
    PORT=$((PORT + 1))
done

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
COMMIT="$(git rev-parse --short HEAD)"
DIRTY=""
git diff --quiet HEAD 2>/dev/null || DIRTY=" (未コミットの変更あり)"

echo "=================================================="
echo " stockManagement ローカル起動"
echo "   ブランチ : $BRANCH @ $COMMIT$DIRTY"
echo "   場所     : $ROOT"
echo "   データ   : data/my_stock_local.csv / $SQLITE_PATH"
if [ "${DEV_USE_CLOUD:-0}" = "1" ]; then
    echo "   注意     : DEV_USE_CLOUD=1 のため .env の GCS / Slack をそのまま使います (本番のデータを書き換えます)"
else
    echo "   クラウド : 使わない (本番の GCS・DB・Slack には触れません)"
fi
echo "   URL      : http://localhost:$PORT"
echo "=================================================="

# --reload: ファイルを保存すると自動で再起動する。python/ 以外 (data/ など) の変更では再起動しない
exec "$PYTHON" -m uvicorn python.web.app:app --reload --reload-dir python --host 127.0.0.1 --port "$PORT"
