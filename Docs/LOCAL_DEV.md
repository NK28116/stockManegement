# ローカルで動かす (make dev)

`develop`、そこから切ったブランチ、`git worktree` のどこでも、同じ手順で Web UI を起動できます。

```bash
make dev
```

起動すると、次のように表示されます。表示された URL をブラウザで開いてください。

```
==================================================
 stockManagement ローカル起動
   ブランチ : feature/xxx @ 5704671
   場所     : /path/to/worktree
   データ   : data/my_stock_local.csv / /path/to/worktree/data/dev/dev.db
   クラウド : 使わない (本番の GCS・DB・Slack には触れません)
   URL      : http://localhost:8888
==================================================
```

**「ブランチ」と「場所」が、確認したいチェックアウトになっているか**を最初に見てください。
別のターミナルで起動したサーバーや、別のディレクトリのサーバーを見ていることが、
「変更が反映されない」の一番多い原因です。

## 何が起きるか

| 項目 | ローカル (make dev) | 本番 |
| --- | --- | --- |
| コード | そのチェックアウトのファイル。保存すると自動で再起動 (`--reload`) | `main` |
| 保有株データ | `data/my_stock_local.csv` | GCS の `my_stock.csv` |
| チャート | `data/plots/1mo/`、`data/chartImg/1mo/` | GCS の `charts/` |
| DB | SQLite (`data/dev/dev.db`) | PostgreSQL |
| ログイン | 不要 | 必要 |
| Slack 通知 | 送らない | 送る |

`.env` に本番の値 (バケット名、`APP_ENV=production` など) が書いてあっても、`make dev` はローカル用の値で上書きします。
画面で購入・削除・編集をしても、本番のデータは変わりません。

`data/` は Git の管理外です。チェックアウトごとに別のデータを持つので、worktree で試した操作が `develop` のデータを変えることもありません。

## データの用意

`data/my_stock_local.csv` が無いときは、自動で用意します。

1. worktree では、メインのチェックアウトの `data/my_stock_local.csv` をコピー (チャート画像と `latest_indicators.json` も)
2. それも無ければ、`data/my_stock.sample.csv` (サンプル) をコピー

サンプルからやり直したいときは、次を実行します。`data/my_stock_local.csv` と SQLite を作り直してから起動します。

```bash
make dev-reset
```

チャートの無い銘柄は「分析待ち」と表示されます。画面の **Update Data** でチャートを作れます
(株価の取得にインターネット接続が必要です)。

## 複数のブランチを同時に動かす

ポートは 8888 から順に、空いている番号を使います。worktree ごとに `make dev` を実行すれば、それぞれ別の URL で動きます。
番号を決めたいときは `DEV_PORT` を指定します。

```bash
DEV_PORT=9000 make dev
```

```bash
git worktree add ../stock-feature feature/xxx
```

```bash
cd ../stock-feature && make dev
```

worktree に `venv` が無ければ、メインのチェックアウトの `venv` を使います。

## うまくいかないとき

| 症状 | 確認すること |
| --- | --- |
| 変更が画面に出ない | 起動時の「ブランチ」「場所」。ブラウザのキャッシュ (Shift + 再読み込み)。HTML の変更は再読み込みで、Python の変更は自動再起動で反映される |
| `uvicorn / fastapi がありません` | `python3 -m venv venv && ./venv/bin/pip install -r requirements.txt` |
| 一覧が空 | `data/my_stock_local.csv` の中身。`make dev-reset` でサンプルに戻す |
| 価格が 0、名前がコードのまま | 株価の取得 (Yahoo Finance) に失敗している。ネットワークを確認する |

## 本番のクラウドにつなぎたいとき (非推奨)

`DEV_USE_CLOUD=1 make dev` で、`.env` の GCS・Slack・GCP の設定をそのまま使います。
**画面の操作で本番の `my_stock.csv` が書き換わり、Slack にも通知が飛びます。** 読み取りの確認だけにしてください。
