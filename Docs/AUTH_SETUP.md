# 単一パスワード認証のセットアップ (PRIDEV-481)

管理画面 / 管理API を未認証アクセスから保護するための設定手順。

レビュー指摘 (PRIDEV-518〜523) の反映内容:

- 保護対象は「公開パス以外すべて」。ルートを追加しても既定で保護される。
- ログイン画面は Jinja2 テンプレート (自動エスケープ) で描画する。
- 本番環境では設定不足で **起動しない** (フェイルクローズ)。
- 平文の `APP_PASSWORD` は受け付けない。ハッシュのみ。
- ログイン試行制限は **単一ワーカー / 単一インスタンス構成専用**。

## 1. パスワードハッシュを生成する

```bash
python scripts/hash_password.py
```

プロンプトへパスワードを入力すると `APP_PASSWORD_HASH=pbkdf2_sha256$...` が出力される。
パスワードはコマンドライン引数で渡さない (シェル履歴へ残るため)。

ローカルでも本番でも、設定するのはこのハッシュだけ。平文を環境変数へ置く手段は存在しない。

## 2. 環境変数を設定する

| 環境変数 | 必須 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `APP_ENV` | ○ (開発時) | (未設定 = 本番扱い) | `local` / `development` / `dev` / `test` / `ci` のいずれかのときだけ開発環境。それ以外・未設定は本番 |
| `APP_PASSWORD_HASH` | ○ (本番) | (なし) | 手順 1 で生成したハッシュ。**本番で未設定・形式不正なら起動しない** |
| `AUTH_SECRET_KEY` | ○ (本番) | 開発のみ起動ごとのランダム値 | セッション Cookie の署名鍵。本番では 32 文字以上が必須 |
| `AUTH_SESSION_MAX_AGE_SECONDS` | - | `43200` (12 時間) | セッション有効期限 |
| `AUTH_MAX_LOGIN_ATTEMPTS` | - | `5` | ロックアウトまでの連続失敗回数 |
| `AUTH_LOCKOUT_SECONDS` | - | `900` (15 分) | ロックアウト時間 |
| `AUTH_PUBLIC_PATH_PREFIXES` | - | `/auth/login,/auth/logout,/api/auth/status,/health,/static` | **認証不要**とするパスの前方一致リスト。これ以外はすべて保護対象 |
| `AUTH_COOKIE_SECURE` | - | 開発は `false` / 本番は常に `true` | Cookie の Secure 属性。本番ではこの値に関係なく `Secure` が付く |
| `AUTH_TRUSTED_PROXY_COUNT` | - | `0` | 信頼するリバースプロキシの段数。`0` なら `X-Forwarded-For` を一切信用しない |
| `WEB_CONCURRENCY` | - | `1` | ワーカー数。本番で `2` 以上だと起動しない (後述) |

`AUTH_SECRET_KEY` は次のように生成できる。

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

本番 (GCP / Render) では `APP_PASSWORD_HASH` と `AUTH_SECRET_KEY` を Secret Manager
またはダッシュボードの Secret へ登録し、環境変数として注入すること。

デプロイ前に済ませておく作業:

| デプロイ先 | 作業 |
| --- | --- |
| Cloud Run | Secret Manager へ `APP_PASSWORD_HASH` / `AUTH_SECRET_KEY` を作成 (ワークフローが `:latest` を参照)。サービスアカウントへ `roles/secretmanager.secretAccessor` を付与 |
| Render | ダッシュボードの Environment で `APP_PASSWORD_HASH` / `AUTH_SECRET_KEY` (`sync: false`) を入力 |

```bash
# Secret Manager への登録例 (平文はコマンド履歴へ残さない)
python scripts/hash_password.py   # 出力の右辺のみを使う
printf '%s' '<生成されたハッシュ>' | gcloud secrets create APP_PASSWORD_HASH --data-file=-
python -c "import secrets; print(secrets.token_urlsafe(32))" \
  | tr -d '\n' | gcloud secrets create AUTH_SECRET_KEY --data-file=-
```

**未登録のままデプロイするとアプリは起動しない** (フェイルクローズ)。
これは意図した挙動で、認証なしで公開されるより安全側に倒している。

### 本番でのフェイルクローズ (PRIDEV-521)

`APP_ENV` が既知の開発値以外 (未設定を含む) のとき、起動時に次を検証し、
満たさなければ `AuthConfigurationError` を送出してアプリを起動しない。

1. `APP_PASSWORD_HASH` が設定されており、形式が正しいこと
2. `AUTH_SECRET_KEY` が設定されており、32 文字以上であること
3. ワーカー数が 1 であること (`WEB_CONCURRENCY` / `UVICORN_WORKERS` / `GUNICORN_WORKERS`)

検証は `lifespan` の先頭で 1 回だけ行う。リクエスト処理中に認証が黙って
無効化されることはない。

認証を無効にできるのは `APP_ENV` が `local` / `development` / `dev` / `test` / `ci`
のときだけ。`APP_ENV` の設定漏れは本番扱いになり、認証なしで起動しない。

### 平文パスワードの取り扱い (PRIDEV-523)

| 保管場所 | 保管するもの |
| --- | --- |
| KeePassXC | 平文パスワード (ここだけ) |
| ローカル `.env` | `scripts/hash_password.py` で生成した `APP_PASSWORD_HASH` のみ |
| 本番 (GCP / Render) | Secret 上の `APP_PASSWORD_HASH` |

**平文パスワードを `.env` / リポジトリ / Issue / 各種フォームへ書かないこと。**
アプリは平文の環境変数を一切読まないため、書いても認証は有効にならない。
`.env` は `.gitignore` 済みだが、そもそも平文を置かない運用とする。
ハッシュから平文は復元できないため、`APP_PASSWORD_HASH` の共有は平文の共有にはあたらない。

## 3. 保護対象と公開ルート (PRIDEV-518)

保護対象は **公開パス以外のすべて**。新しいルートを追加しても既定で保護される。

認証なしで到達できるのは次のパスだけ。

| パス | 公開する理由 |
| --- | --- |
| `/auth/login` | ログインフォームそのもの。常に公開 (設定で外せない) |
| `/auth/logout` | Cookie を破棄するだけで、未認証で叩いても安全 |
| `/api/auth/status` | 画面が認証状態を判定するための最小情報のみ返す |
| `/health` | 外形監視 / PaaS のヘルスチェック。認証を要求すると死活監視が常に失敗する |
| `/static` | 認証前のログイン画面が参照する静的アセット |

保護される既存の画面 / API (`tests/test_auth.py` のパラメタライズドテストで検証):

| 種別 | パス |
| --- | --- |
| 画面 | `/`, `/system-monitor` |
| API | `/api/rules/*`, `/api/signals/*`, `/api/charts/*`, `/api/simulate/*`, `/api/actions/*`, `/api/analytics/*`, `/api/watchlist/*`, `/api/system-monitor/*` |
| 開発用 | `/docs`, `/openapi.json` |

多層防御として、middleware に加えて管理ルーターの `include_router()` にも
`dependencies=[Depends(require_auth)]` を付与している。middleware の設定を誤っても
管理 API へ認証なしで到達しない。

## 4. ログイン試行制限の対応構成 (PRIDEV-522)

**対応するデプロイ構成: 単一ワーカー / 単一インスタンス。**

失敗回数はプロセス内の辞書で保持するため、複数ワーカーでは上限を迂回できる。
そのため本番では `WEB_CONCURRENCY` などが 2 以上だと起動時に失敗する。
分散構成へ移行する場合は Redis 等の共有ストア、または外部レートリミッターへ
差し替えること (`python/web/auth.py` の `_login_attempts` 周辺)。

クライアント識別:

- `AUTH_TRUSTED_PROXY_COUNT=0` (既定): `X-Forwarded-For` を無視し、TCP 接続元を使う
- `AUTH_TRUSTED_PROXY_COUNT=N` (N>=1): `X-Forwarded-For` の右から N 番目を実クライアント
  とする。末尾 N-1 個は信頼済みプロキシ自身のアドレス、それより左はクライアントが
  自称した値なので信用しない

Render / Cloud Run はプロキシ 1 段構成のため `1` を指定する (`render.yaml` 設定済み)。

辞書はロックアウト期間を過ぎたエントリを毎回全体清掃し、追跡クライアント数の上限
(`MAX_TRACKED_CLIENTS = 1024`) を超えたら古い順に破棄するため、無制限に増加しない。

## 5. 動作確認

| 操作 | 期待結果 |
| --- | --- |
| 未認証で保護対象 API へアクセス | `401` |
| 未認証で保護対象画面へアクセス | `/auth/login?next=<元のpathとquery>` へリダイレクト |
| `/auth/login` へ正しいパスワードを POST | `303` + セッション Cookie 発行 |
| ログイン後 | `next` の path と query の両方へ復帰 |
| 誤ったパスワードを POST | `401` (Cookie は発行されない) |
| `AUTH_MAX_LOGIN_ATTEMPTS` 回失敗後 | `429` (`AUTH_LOCKOUT_SECONDS` 経過まで) |
| ロックアウト時間経過後 | 正しいパスワードでログインできる |
| `/auth/logout` を POST | Cookie 破棄。再び `401` |
| 本番で `APP_PASSWORD_HASH` / `AUTH_SECRET_KEY` 未設定 | 起動失敗 |

自動テスト:

```bash
PYTHONPATH=. pytest tests/test_auth.py -v
```

## 6. 認証必須ルートの追加方法

新しいルートは **何もしなくても保護される**。公開したい場合のみ
`AUTH_PUBLIC_PATH_PREFIXES` へ追加し、その理由を本 Docs の表へ記載すること。

管理ルーターを新設する場合は、多層防御のため `include_router()` にもガードを付ける。

```python
# python/web/app.py
app.include_router(new_admin.router, dependencies=[Depends(auth.require_auth)])
```

個別ルートへ付ける場合:

```python
from fastapi import Depends
from python.web.auth import require_auth

@router.get("/api/system-monitor", dependencies=[Depends(require_auth)])
async def system_monitor():
    ...
```

## セキュリティ上の注意

- パスワード・Cookie 値・ハッシュはログへ出力しない実装になっている (`tests/test_auth.py` で検証)。
- ログイン画面は Jinja2 の自動エスケープで描画する。動的値を文字列連結や `str.format` で
  HTML へ埋め込まないこと (反射型 XSS になる / PRIDEV-519)。
- `next` は「リダイレクト先としての検証」と「HTML 属性値としてのエスケープ」を分けて行う。
  検証は同一オリジンの相対 URL のみ許可し、scheme / netloc / バックスラッシュ / 制御文字を弾く。
- セッション Cookie は `HttpOnly` / `SameSite=Lax` / (本番では必ず) `Secure` 付きで発行される。
- 複数ユーザー管理・OAuth/OIDC・ロール権限は本チケットの対象外。
