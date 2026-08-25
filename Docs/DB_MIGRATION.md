# DB マイグレーション運用手順 (PRIDEV-487)

## 前提

- スキーマの正は `python/db/models.py`
- マイグレーションは `alembic/versions/` (head: `0003`)
- **SQLite モードは import 時に `Base.metadata.create_all()` が走る**ため、
  テーブルは出来ているが `alembic_version` が無い状態になりうる。
  この場合は `alembic stamp head` で履歴だけを揃える (下記フロー参照)

## 1. 差分を確認する

```bash
make db-check
# または
PYTHONPATH=. python -m python.db.schema_check          # 人間向け
PYTHONPATH=. python -m python.db.schema_check --json   # 機械可読
```

このコマンドは **読み取り専用**で、DDL を一切実行しない。確認内容:

- DB の `alembic_version` と `alembic/versions` の head が一致するか
- `python/db/models.py` が定義する全テーブル (`signals` / `watchlist` /
  `stock_notes` / `portfolio` / `stocks` / `daily_prices` / `signal_history`) が存在するか

整合していれば終了コード 0、差分があれば 1 を返す。

## 2. 結果ごとの対応

| 検出内容 | 意味 | 対応 |
| --- | --- | --- |
| `[OK]` | 整合済み | 対応不要 |
| `DB が未初期化です` | 空の DB | `alembic upgrade head` |
| `既存 DB が Alembic の管理下にありません` | `create_all` で作られた DB。テーブルはあるが履歴が無い | スキーマが最新なら **`alembic stamp head`**、古いなら `alembic upgrade head` |
| `DB のリビジョンが head と一致しません` | 未適用のマイグレーションがある | `alembic upgrade head` |
| `必要テーブルが存在しません` | テーブル欠落 | `alembic upgrade head` |

```bash
PYTHONPATH=. python -m alembic upgrade head   # マイグレーション適用
PYTHONPATH=. python -m alembic stamp head     # 履歴だけ現在地へ合わせる (DDL なし)
```

`stamp` は DDL を実行しないため、**既存データを再作成・削除しない**。

## 3. 本リビジョンで解消した不整合

1. `alembic/env.py` が `python.db.database` を import しており、SQLite では
   **マイグレーション実行前に `create_all()` が走ってしまい**
   `alembic upgrade head` が「table signals already exists」で失敗していた。
   URL 組み立てを副作用のない `python/db/url.py` へ切り出して解消。
2. `portfolio` / `stocks` / `daily_prices` / `signal_history` が
   マイグレーション履歴に存在せず、新規 DB へ `alembic upgrade head` しても
   作られなかった。リビジョン `0003` で履歴へ取り込んだ。
   `0003` は **存在しないテーブルだけ**を作るため、既存 DB では何もしない。

## 4. マイグレーションを追加するとき

```bash
PYTHONPATH=. python -m alembic revision --autogenerate -m "説明"
# 生成物を必ず目視確認してから
PYTHONPATH=. python -m alembic upgrade head
make db-check
```

既存テーブルへ触れる場合は `downgrade()` でデータが消えないかを必ず確認する。

## 5. 回帰テスト

```bash
PYTHONPATH=. pytest tests/test_schema_consistency.py -v
```

一時 SQLite 上で新規 DB / 既存 DB の双方を作り、
migration の適用・冪等性・既存データが失われないことを検証している。
