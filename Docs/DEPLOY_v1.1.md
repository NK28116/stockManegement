# v1.1 デプロイ手順 (チェックリスト)

`develop` (v1.1) を `main` へマージして本番に出すまでの手順です。上から順に進めてください。

## 本番の構成とデプロイの流れ

| 部分 | 動いている場所 | `main` へ push したときに起きること |
| --- | --- | --- |
| Web UI | Render | Render のダッシュボードで追跡ブランチが `main` なら自動デプロイ (`render.yaml` の `autoDeploy: true`) |
| 日次バッチ・DB | GCE | `.github/workflows/deploy-gce.yml` が IAP 経由の SSH で `git pull` → `pip install` (設定: `Docs/DEPLOY_GCE.md`) |
| (旧) Cloud Run | Cloud Run | `.github/workflows/google-cloudrun-docker.yml` はテストのみ (lint・整形・pytest)。Cloud Run へのデプロイは手動実行のときだけ |

## 今回のデプロイで気をつけること

1. **Render は秘密情報が無いと起動しない。** 本番で `APP_PASSWORD_HASH` / `AUTH_SECRET_KEY` が無いと、アプリは起動に失敗します (フェイルクローズ)。必ず先に設定してください。Render はデプロイに失敗すると前の版を動かし続けます。
2. **GCE の個人データ。** 保有株 CSV などを Git の管理対象から外しました。`deploy-gce.yml` は、これらを退避してから pull し、終わったら書き戻します。退避先は `~/stock-private-backup/<日時>/` です。
3. **GCE の `.env` に `GCS_BUCKET_NAME` が必要。** バケット名をコードに書かなくなりました。無い場合、`deploy-gce.yml` は更新せずに止まり、旧コードのまま動き続けます。

---

## 1. 事前確認 (マージ前)

### Render

- [ ] ダッシュボードで、Web サービスが追跡しているブランチを確認する (`main` のはず)。
      `develop` を追跡している場合は、v1.1 の push ですでにデプロイが試みられています。Events で失敗していないか確認する
- [ ] 環境変数を設定・確認する

| 変数 | 値 | 備考 |
| --- | --- | --- |
| `APP_PASSWORD_HASH` | `python scripts/hash_password.py` の出力 | **新規・必須** |
| `AUTH_SECRET_KEY` | 32 文字以上のランダムな文字列 | **新規・必須**。Bitwarden に控えを置く |
| `APP_ENV` | `production` | 新規 |
| `AUTH_TRUSTED_PROXY_COUNT` | `1` | 新規 |
| `WEB_CONCURRENCY` | `1` | 新規。ログイン試行制限が単一プロセス前提のため |
| `GCS_BUCKET_NAME` / `CLOUD_PG_HOST` / `GOOGLE_CLOUD_PROJECT` | 今の値 | `render.yaml` から値を外した (`sync: false`)。**値が残っているか確認** |
| `GCP_PROJECT_ID` | プロジェクト ID | System Monitor を使う場合のみ |

- [ ] Health Check Path を `/health` にする (`/` はログインが必要になったため)

### GCE

SSH でログインし、リポジトリのディレクトリで実行します。

- [ ] `.env` に `GCS_BUCKET_NAME=<バケット名>` があることを確認する
- [ ] DB をバックアップする

```bash
pg_dump -Fc -f ~/stock_db_before_v1.1.dump <DB名>
```

- [ ] 保有株 CSV を手動でも控えておく (自動退避の保険)

```bash
mkdir -p ~/stock-private-backup/manual && cp -p data/my_stock*.csv ~/stock-private-backup/manual/
```

- [ ] (任意) DB の状態を見ておく (読み取りのみ)。`schema_check` は v1.1 で追加したコマンドで、
      デプロイ前の GCE にはまだ無いため、`psql` で直接確認する。正式な確認は手順 3 で行う

```bash
psql -h localhost -U <DBユーザー> -d <DB名> -c "select version_num from alembic_version;" -c "\dt"
```

- [ ] リポジトリの持ち主 (cron と自動デプロイを動かすユーザー) と、GitHub の Secrets `GCE_USERNAME` が一致していることを確認する
      (自動デプロイの設定は `Docs/DEPLOY_GCE.md`)。
      別のユーザーで SSH した場合は、`sudo -u <持ち主>` を付けて実行する

### GCS

- [ ] 本番の `my_stock.csv` を控えておく (移行スクリプトも自動で控えるが、念のため)

```bash
gcloud storage cp gs://<バケット名>/my_stock.csv gs://<バケット名>/backups/my_stock.csv.before-v1.1
```

### GitHub

- [ ] リポジトリの Settings → Secrets and variables → Actions → Variables に `GCS_BUCKET_NAME` を追加する
      (Cloud Run のワークフロー用。Cloud Run を使っていなければ不要)

### 手元

- [ ] テストを実行する。失敗が既知の 7 件 (`test_analyze_logic.py` / `test_signals_api.py`) だけであること

```bash
PYTHONPATH=. pytest tests
```

## 2. デプロイ

- [ ] `develop` → `main` の PR を作り、マージする (fast-forward で取り込める状態)
- [ ] GitHub Actions の「Deploy to GCE」が成功したことを確認する。ログに `退避しました: ...` が出ていれば、個人データは退避・書き戻し済み
- [ ] Render の Events でデプロイが「Live」になったことを確認する

## 3. デプロイ後の確認

- [ ] `https://<RenderのURL>/health` が `{"status":"ok"}` を返す
- [ ] ログイン画面が出る。正しいパスワードでログインでき、間違ったパスワードは拒否される
- [ ] ダッシュボードが表示され、一覧が「保有中 → 次回購入 → 売却予定 → 監視中 → 除外」の順で並ぶ
- [ ] System Monitor が開ける (GCP の設定が無ければ「一部取得不可」で正常)
- [ ] GCE で、保有株 CSV が残っていることを確認する

```bash
ls -l data/my_stock*.csv
```

- [ ] GCE で日次バッチを 1 回手動実行し、ログにエラーが無いことを確認する

```bash
bash scripts/cron_daily.sh && tail -n 30 log/cron_daily.log
```

- [ ] DB の状態を確認する (読み取りのみ)

```bash
./venv/bin/python -m python.db.schema_check
```

- [ ] 結果に応じて対応する (`Docs/DB_MIGRATION.md`)。`[OK]` 以外のときだけ:

```bash
./venv/bin/python -m alembic stamp head     # テーブルはあるが履歴が無い場合
./venv/bin/python -m alembic upgrade head   # 未適用のマイグレーションがある場合
```

> **本番 GCE の状態 (2026-10-28 確認)**: `alembic_version` に、このリポジトリに無いリビジョン `3c1e05e2ae65`
> が記録されている。必要テーブルはすべて存在するため、デプロイ後に次の 1 回だけ実行する
> (`alembic_version` の中身を入れ替えるだけで、テーブルとデータは変更しない)。
>
> ```bash
> ./venv/bin/python -m alembic stamp --purge head
> ```

## 4. 銘柄ステータスの移行

古い日本語ステータスを英字キーへ置き換えます。チャート一覧 API は、移行前でも旧値を英字キーに直して返します。そのため、この手順はデプロイ後に落ち着いて実施して構いません。詳細は `Docs/STOCK_STATUS.md` を参照してください。

```bash
./venv/bin/python scripts/migrate_stock_status.py --gcs --db
```

- [ ] 終了コード 0 で、「解決できない値」が無いことを確認する。ある場合は、元データを手で直してから再実行する

```bash
./venv/bin/python scripts/migrate_stock_status.py --apply --gcs --db
```

- [ ] もう一度、オプション無し (dry-run) で実行し、「変更 0 件」になることを確認する

## 5. 切り戻し

### 切り戻しの判断基準

- `/health` が 5 分以上 200 を返さない
- 正しいパスワードでログインできない、またはダッシュボードがエラーになる
- 日次バッチが失敗する
- 移行後に、保有中の銘柄が保有中として表示されない

### 手順

| 対象 | 方法 |
| --- | --- |
| Render | ダッシュボードの Events から、前のデプロイを選んで Rollback |
| GCE のコード | `git checkout <マージ前の main のコミット>`。個人データは `~/stock-private-backup/` から戻す |
| GCS の `my_stock.csv` | `gcloud storage cp gs://<バケット名>/backups/my_stock.csv.before-v1.1 gs://<バケット名>/my_stock.csv` |
| DB | 移行は `portfolio.status` の UPDATE のみ。戻す場合は、事前の `pg_dump` から `pg_restore` する |

## 6. 完了後

- [ ] Linear の v1.1 の課題を Done にする
- [ ] 確認が済んだら、`.env.bak` や不要な退避ファイルを整理する (中に秘密情報や個人データが残るため)
