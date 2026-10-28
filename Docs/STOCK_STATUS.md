# 銘柄ステータスと保有目的 (PRIDEV-486)

選択肢の定義とデータ移行手順。

## 単一の定義元

| 対象 | 定義元 |
| --- | --- |
| 銘柄ステータス (`status`) | `python/trading/stock_status.py` |
| 保有目的 (`purpose`) | `python/web/constants.py` |

UI は `GET /api/choices` からこの定義を取得する。**テンプレートへ選択肢を書かないこと**
(`tests/test_choices.py` が検知する)。

## 銘柄ステータス (8 種)

保存値は英字キー、表示は日本語。

| 保存値 | 表示名 | 保有判定 |
| --- | --- | :-: |
| `HOLDING` | 保有中 | 保有 |
| `NEXT_BUY` | 次回のスイングで購入 | 未保有 |
| `SELL_PLANNED_PROFIT` | 売却予定（利益確定） | 保有 |
| `SELL_PLANNED_LOSS` | 売却予定（損切り） | 保有 |
| `SOLD_PROFIT` | 売却済み（利益確定） | 未保有 |
| `SOLD_LOSS` | 売却済み（損切り） | 未保有 |
| `WATCHING` | 監視中 | 未保有 |
| `EXCLUDED` | 除外 | 未保有 |

**売却予定と売却済みは保存値を分離している。** 売却予定はまだ株を持っているため保有、
売却済みは未保有として扱う。保有判定は `stock_status.is_held()` /
`stock_status.held_status_values()` を使い、SQL や画面で作り直さない。

## 保有目的 (4 種)

| 保存値 | 表示名 |
| --- | --- |
| `long` | 長期（バリュー投資） |
| `middle` | 中期 |
| `present` | 優待目的 |
| `swing` | スイングトレード |

## 選択肢を増減させるとき

1. ステータスなら `python/trading/stock_status.py` の `STATUS_CHOICES`、
   目的なら `python/web/constants.py` の `PURPOSE_CHOICES` へ追記する
2. 既存データへ新しい保存値を入れる場合は移行手順 (下記) を実行する
3. `PYTHONPATH=. pytest tests/test_stock_status.py tests/test_choices.py` を実行する

画面・API・並び順・バッジ表示はすべて定義から導出されるため、他の変更は不要。

## データ移行手順

旧データは `status` へ日本語の表示文字列を保存していた。英字キーへ移行する。
移行対象は 3 か所ある。

| 対象 | 誰が読むか | オプション |
| --- | --- | --- |
| `data/my_stock.csv` / `data/my_stock_local.csv` | ローカル開発・バッチ | (既定) |
| GCS `gs://$GCS_BUCKET_NAME/my_stock.csv` | **本番のチャート一覧** | `--gcs` |
| `portfolio` テーブル | シグナル API ほか | `--db` |

### 実行順 (本番)

```bash
# 0. 新しいアプリをデプロイする
#    チャート一覧 API は旧ラベルを英字キーへ正規化して返すため、
#    移行前でも誤った保有表示にはならない (解決できない値は未保有扱い)。

# 1. 差分を確認する (既定は dry-run。何も書き換えない)
PYTHONPATH=. python scripts/migrate_stock_status.py --gcs --db

# 2. 終了コード 0 (解決できない値なし) を確認してから適用する
PYTHONPATH=. python scripts/migrate_stock_status.py --apply --gcs --db

# 3. 再度 dry-run し「変更 0 件」になったことを確認する
PYTHONPATH=. python scripts/migrate_stock_status.py --gcs --db
```

- GCS は `GCS_BUCKET_NAME` (または `--gcs-bucket`) のバケットを対象にする。
  実行者には対象バケットへの読み書き権限が必要
- 適用前のファイルは CSV なら `<名前>.bak-YYYYmmddHHMMSS`、GCS なら
  `backups/my_stock.csv.bak-YYYYmmddHHMMSS` に保存される。復元は
  `gsutil cp gs://<bucket>/backups/my_stock.csv.bak-<日時> gs://<bucket>/my_stock.csv`
- GCS は読み込んだ時点の generation を条件に上書きする。移行中に他から更新されて
  いれば上書きせずに失敗するので、再度 dry-run からやり直す
- `portfolio` は主キー `id` 単位で 1 行ずつ、1 トランザクションで更新する。
  同じ `code` の行が複数あっても互いに上書きしない

### 「売却（…）」の解決ルール

`sell_stock()` は売却時に数量を 0 にする。したがって

| 旧ラベル | 保有数量 | 移行後 |
| --- | --- | --- |
| 売却（利益確定） | > 0 | `SELL_PLANNED_PROFIT` (売却予定として運用されていた) |
| 売却（利益確定） | 0 | `SOLD_PROFIT` |
| 売却（損切り） | > 0 | `SELL_PLANNED_LOSS` |
| 売却（損切り） | 0 | `SOLD_LOSS` |
| 売却（…） | 欠損・非数値 | **解決できない値** (推測しない) |

解決できない値 (例: 数量が空の売却ラベル、利確/損切りの区別が無い「売却」) は報告し、
終了コード 1 を返す。**1 件でもあれば `--apply` でもどの対象も書き換えない**
(CSV / GCS / DB の一部だけが移行された状態を作らない)。手動で修正してから再実行すること。

移行は冪等で、`UPDATE` のみを行う (テーブルの再作成・行削除はしない)。

### 移行前後の互換性

- チャート一覧 API (`/api/charts/list`) は旧ラベルを英字キーへ正規化して返す。
  解決できない値は元の文字列のまま返し、画面では未保有扱いになる
- `stock_status.normalize()` / `is_held()` も旧ラベルを解釈する
- `refresh_prices()` の有効ステータス判定は旧ラベルを許容しているため、
  移行前に実行しても行が削除されることはない
