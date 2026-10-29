# GCE への自動デプロイ

`main` に push すると、GitHub Actions の「Deploy to GCE」(`.github/workflows/deploy-gce.yml`) が
GCE 上のリポジトリを更新します (`git pull` → `pip install`)。

## しくみ

GCE の SSH (22 番) はインターネットに開いていません。そこで、次の順に接続します。

```
GitHub Actions
  │ 1. Workload Identity 連携で、デプロイ専用のサービスアカウントとしてログイン (鍵ファイル不要)
  ▼
Google Cloud
  │ 2. IAP トンネル経由で SSH (OS Login)
  ▼
GCE
    3. sudo -u <リポジトリの持ち主> で scripts/deploy_gce.sh を実行
```

- GitHub に保存する SSH 鍵やサービスアカウント鍵はありません。GitHub が発行する短命のトークンを Google Cloud が検証します。
- サービスアカウントを使えるのは、このリポジトリのワークフローだけです。
- OS Login (sudo あり) の権限は、対象のインスタンスにだけ付けています。
- 更新の中身は `scripts/deploy_gce.sh` です。GCE 上で手動でも実行できます。

```bash
sudo -u <リポジトリの持ち主> bash scripts/deploy_gce.sh /home/<リポジトリの持ち主>/stockManegement
```

`deploy_gce.sh` は次のときに更新せず止まります。旧コードのまま動き続けます。

- `.env` に `GCS_BUCKET_NAME` が無い
- サーバー上でコミットされているなど、fast-forward で更新できない
- 管理下のファイルの中身がサーバー上で書き換えられている (`Your local changes ... would be overwritten`)

実行権限だけの変更 (サーバー上での `chmod`) は、止まらずに管理下の版へ戻してから更新します。

## 初回の設定 (1 回だけ)

### 1. GCP

`gcloud` にプロジェクトのオーナー権限でログインした状態で、リポジトリのルートで実行します。
Workload Identity のプール `github-actions-pool-1` とプロバイダー `github-actions-provider-1` が無ければ作ります。
プロバイダーは、このリポジトリのワークフローが発行したトークンだけを受け付けます。

```bash
GCE_INSTANCE=<インスタンス名> GCE_ZONE=<ゾーン> bash scripts/setup_gce_deploy.sh
```

何度実行しても同じ結果になります。最後に、GitHub に登録する値が表示されます。
`WARNING` が出た場合は、OS Login か IAP 用のファイアウォールルールが無いので、先に設定してください。

### 2. GitHub

Settings → Secrets and variables → Actions → **Secrets** に登録します。
公開リポジトリの Actions のログは誰でも読めるため、インスタンス名などの識別子も Secrets に入れます (ログでは `***` になります)。

| Secret | 値 |
| --- | --- |
| `GCE_WIF_PROVIDER` | `projects/<番号>/locations/global/workloadIdentityPools/github-actions-pool-1/providers/github-actions-provider-1` |
| `GCE_DEPLOY_SERVICE_ACCOUNT` | `gce-deployer@<GCP_PROJECT_ID>.iam.gserviceaccount.com` |
| `GCE_INSTANCE` | インスタンス名 |
| `GCE_ZONE` | ゾーン |
| `GCE_USERNAME` | リポジトリの持ち主 (cron を動かすユーザー)。登録済みならそのまま |

以前の SSH 方式で使っていた `GCE_HOST` と `GCE_SSH_KEY` は不要になったので削除してください。
`GCE_SSH_KEY` に対応する公開鍵が GCE の `~/.ssh/authorized_keys` に残っていれば、それも消します。

### 3. 動作確認

Actions → 「Deploy to GCE」→ **Run workflow** (ブランチは `main`) で手動実行し、
ログの最後に `デプロイ完了: <前のコミット> -> <今のコミット>` が出ることを確認します。

## うまくいかないとき

| エラー | 原因と対処 |
| --- | --- |
| `Permission 'iam.serviceAccounts.getAccessToken' denied` / `invalid_target` | Workload Identity の紐付けが無い。`setup_gce_deploy.sh` を再実行する |
| `failed to connect to backend` / `4033: not authorized` | IAP の権限かファイアウォールルールが無い |
| `Permission denied (publickey)` | OS Login の権限が無いか、OS Login が無効 |
| `sudo: a password is required` | OS Login の権限が `osLogin` (sudo なし) になっている。`osAdminLogin` を付ける |
| `ERROR: .env に GCS_BUCKET_NAME がありません` | GCE の `.env` にバケット名を書く |
| `fatal: Not possible to fast-forward` | GCE 上でコミットや変更がある。`git status` / `git log` で確認して片付ける |
| `Your local changes to the following files would be overwritten by merge` | GCE 上で管理下のファイルが編集されている。`git diff` で中身を確認し、不要なら `git checkout -- <ファイル>` で戻す |
