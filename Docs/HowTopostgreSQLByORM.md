# GCE上でのORMを用いたPostgreSQL操作ガイド

本プロジェクトでは、データベース操作に **SQLAlchemy** (ORM) と **Alembic** (マイグレーション) を使用しています。
GCEインスタンス上でデータベースのスキーマ変更やデータ操作を行う手順を以下に示します。

## 1. 前提条件

GCEインスタンスにSSH接続し、プロジェクトのルートディレクトリにいることを前提とします。
また、操作は仮想環境内で行う必要があります。

```bash
# プロジェクトディレクトリへ移動
cd ~/stockManegement

# 仮想環境の有効化
source .venv/bin/activate
```

## 2. データベーススキーマの変更 (マイグレーション)

テーブル定義 (`python/db/models.py`) を変更した場合、Alembicを使用してデータベースに反映させます。

### 手順

1. **モデルの修正**:
    `python/db/models.py` を編集して、テーブル定義（カラムの追加・変更など）を行います。

2. **マイグレーションファイルの作成**:
    Alembicにモデルの変更を検知させ、マイグレーションスクリプトを自動生成します。

    ```bash
    alembic revision --autogenerate -m "変更内容の説明（例: Add sector column）"
    ```

    * 生成されたファイルは `alembic/versions/` に保存されます。
    * 意図した変更が含まれているかファイルの中身を確認することを推奨します。

3. **マイグレーションの適用**:
    作成したマイグレーションスクリプトを実行し、データベースに変更を適用します。

    ```bash
    alembic upgrade head
    ```

### その他のコマンド

* **現在のリビジョン確認**: `alembic current`
* **履歴確認**: `alembic history`
* **1つ前の状態に戻す**: `alembic downgrade -1`

## 3. Pythonスクリプトによるデータ操作

PythonシェルやスクリプトからORMを使ってデータを操作する方法です。

### Pythonシェルでの操作例

```bash
# 仮想環境内でPythonシェルを起動
python3
```

```python
# 必要なモジュールのインポート
from python.db.database import get_db_session
from python.db.models import Stock, DailyPrice, Portfolio

# セッションを使用してDB操作
with get_db_session() as session:
    # --- データの取得 (SELECT) ---
    stocks = session.query(Stock).limit(5).all()
    for stock in stocks:
        print(f"{stock.code}: {stock.name}")

    # --- データの追加 (INSERT) ---
    # new_stock = Stock(code="9999", name="Test Stock", market="Prime")
    # session.add(new_stock)
    # session.commit()  # 変更を確定

    # --- データの更新 (UPDATE) ---
    # target = session.query(Stock).filter(Stock.code == "9999").first()
    # if target:
    #     target.name = "Updated Name"
    #     session.commit()
```

## 4. 直接SQLを実行して確認する場合 (参考)

ORMを経由せず、Dockerコンテナ内のPostgreSQLに直接接続して確認する場合の手順です。

```bash
# 実行中のDBコンテナに入り、psqlを起動 (コンテナ名 stock-db, ユーザー user, DB名 stock_db の場合)
docker exec -it stock-db psql -U user -d stock_db
```

* **テーブル一覧表示**: `\dt`
* **テーブル定義確認**: `\d table_name`
* **クエリ実行**: `SELECT * FROM stocks LIMIT 5;`
* **終了**: `\q`

## 5. トラブルシューティング

### DBコンテナのログ確認

データベースが起動しない、接続できない等の問題が発生した場合、コンテナのログを確認します。

```bash
# ログを表示
docker logs stock-db

# ログをリアルタイムで監視 (Ctrl+Cで終了)
docker logs -f stock-db
```

### マイグレーション失敗時のリカバリ

`alembic upgrade head` がエラーで失敗した場合の対処法です。

1.  **エラー内容の確認**:
    PostgreSQLはDDL（テーブル作成など）もトランザクション管理されるため、基本的には失敗時に自動でロールバックされ、DBの状態は変更前のまま維持されます。
    エラーメッセージを読み、マイグレーションスクリプト (`alembic/versions/xxxx.py`) のバグを修正して再度実行してください。

2.  **適用済みの変更を取り消したい場合**:
    直前のマイグレーションを取り消すには `downgrade` を使用します。
    ```bash
    alembic downgrade -1
    ```

3.  **マイグレーションファイルの再作成**:
    まだ `upgrade` していないマイグレーションファイルを作り直したい場合は、単にそのファイルを削除し、`models.py` を修正してから再度 `alembic revision --autogenerate` を実行してください。
