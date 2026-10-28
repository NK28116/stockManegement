# Bitwarden で秘密情報を管理し、.env を生成する

パスワードのハッシュや署名鍵、DB パスワード、バケット名などはリポジトリに書かず、Bitwarden に保存します。
手元の `.env` は、[chezmoi](https://www.chezmoi.io/) のテンプレート機能で Bitwarden から生成します。

```
Bitwarden の項目「stockManagement」
  └ カスタムフィールド (APP_PASSWORD_HASH, AUTH_SECRET_KEY, GCS_BUCKET_NAME, ...)
        │  bw get item  (Bitwarden CLI)
        ▼
.env.chezmoi.tmpl  ──  make env (chezmoi execute-template)  ──▶  .env (権限 600 / コミットしない)
```

テンプレート `.env.chezmoi.tmpl` は秘密を含まないのでリポジトリに置いています。
項目のカスタムフィールドを、**フィールド名をそのまま環境変数名として**すべて書き出します。
新しい秘密が増えたときは、Bitwarden にフィールドを足して `make env` を実行し直すだけです。

## 1. 必要なツール

```bash
brew install chezmoi bitwarden-cli
```

chezmoi を dotfiles の管理に使っていなくても、`make env` だけのために入れて構いません。

## 2. Bitwarden に項目を作る

1. Bitwarden で「ログイン」型の項目を作り、名前を **`stockManagement`** にします。
2. 「カスタムフィールド」に、環境変数名と値を登録します。秘密の値は種類を「非表示」にします。

| フィールド名 | 種類 | 中身 |
| --- | --- | --- |
| `APP_PASSWORD_HASH` | 非表示 | `python scripts/hash_password.py` の出力。平文のパスワードは項目のパスワード欄にだけ保存する |
| `AUTH_SECRET_KEY` | 非表示 | `python -c "import secrets; print(secrets.token_urlsafe(32))"` の出力 |
| `GCS_BUCKET_NAME` | テキスト | GCS バケット名 (ローカルで GCS を使うときだけ) |
| `GCP_PROJECT_ID` | テキスト | GCP プロジェクト ID (System Monitor をローカルで使うときだけ) |
| `LOCAL_PG_PASSWORD` など | 非表示 | PostgreSQL を使う場合の接続情報 |
| `SLACK_WEBHOOK_URL` / `SLACK_BOT_TOKEN` | 非表示 | Slack 通知を使う場合 |
| `MCP_API_KEY` | 非表示 | MCP サーバーを HTTP で公開する場合 |

- フィールド名は英大文字・数字・`_` だけにします。それ以外の名前は `.env` に書き出さずにスキップします。
- テンプレートには `APP_ENV=local` などの既定値が入っています。同じ名前のフィールドを作ると、フィールドの値が優先されます。
- 項目名が他の項目とかぶると `bw get` が失敗します。そのときは項目 ID を使います:
  `STOCK_BW_ITEM=<項目ID> make env`

## 3. .env を生成する

Bitwarden CLI にログインし、保管庫のロックを解除してから実行します。

```bash
bw login
```

```bash
export BW_SESSION="$(bw unlock --raw)"
```

```bash
make env
```

- 生成した `.env` の権限は 600 (自分だけ読み書き可) です。
- 既存の `.env` は `.env.bak` に退避します。生成に失敗したときは、既存の `.env` を変更しません。
- `.env`・`.env.bak`・作業ファイルの `.env.tmp` は `.gitignore` 済みです。

毎回 `bw unlock` を打つのが面倒なら、chezmoi の設定 (`~/.config/chezmoi/chezmoi.toml`) に次を書くと、
`BW_SESSION` が無いときに chezmoi がロック解除を求めてくれます。

```toml
[bitwarden]
    unlock = "auto"
```

## 4. 値を変えたとき (ローテーション)

1. Bitwarden のフィールドを新しい値に更新します。
2. `bw sync` で手元の CLI に反映してから、`make env` を実行します。
3. 本番の値は別に更新が必要です (Render のダッシュボード、GCP の Secret Manager、GCE の `.env`)。
   `AUTH_SECRET_KEY` を変えると、ログイン中の全員がログアウトされます。

## 5. 本番環境では

本番の秘密は今までどおり各環境の仕組みで管理します (Render のダッシュボード、GCP の Secret Manager、GitHub Actions の Secrets / Variables)。
Bitwarden は、それらに登録した値の控えとしても使えます。

GCE の毎日のバッチ (`scripts/cron_daily.sh`) も `.env` を読みます。GCE 上で `make env` を使う場合は、
対話なしでロック解除できないので、[Bitwarden Secrets Manager](https://bitwarden.com/products/secrets-manager/) の
CLI (`bws`) とアクセストークンを使う方法が向いています。chezmoi では `bitwardenSecrets` 関数で読めます。

## 6. GCP の認証情報について

ローカルから GCS や Cloud Logging を使うときは、サービスアカウントの鍵ファイルを配るより、
自分の Google アカウントで次のコマンドを実行する方法をおすすめします。鍵ファイルを管理する必要がなくなります。

```bash
gcloud auth application-default login
```

どうしても鍵ファイルが必要な場合は、Bitwarden の項目に添付ファイルとして保存し、chezmoi の
`bitwardenAttachmentByRef` 関数で取り出せます。取り出した鍵はリポジトリの外 (例: `~/.config/gcloud/`) に置いてください。
