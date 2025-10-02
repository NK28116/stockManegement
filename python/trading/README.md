# `trading` ディレクトリ

このディレクトリには、株の取引戦略と実行に関連するモジュールが含まれています。保有銘柄の管理、取引履歴の記録、売買タイミングの分析などを行います。

## ファイル一覧

- `buy_and_sell_stock.py`:
  保有銘柄の購入、売却、ステータス・目的の更新、過去の取引履歴の記録など、`my_stock.csv`とデータベースの操作を管理します。

- `every_stock_buy_and_sell_timing.py`:
  個々の銘柄に対する売買タイミングを決定するための戦略やアルゴリズムを実装し、全銘柄の一括分析を行います。

- `trading_rules.py`:
  取引を行う上での各種ルールや条件を定義します。リスク管理、資金管理、取引制限などが含まれます。

## `buy_and_sell_stock.py` の機能と使い方

`buy_and_sell_stock.py` は、`my_stock.csv` およびデータベースの `stocks`, `portfolio_holdings`, `transactions` テーブルを操作するためのコマンドラインツールです。

### コマンド一覧

1. **株の購入 (`buy`)**:
    - 指定した銘柄を数量と価格で購入し、`my_stock.csv`を更新します。
    - `--purpose`オプションで目的（`present`, `middle`, `long`, `swing`）を指定できます。

    ```bash
    python3 -m python.trading.buy_and_sell_stock buy 9202.T 10 --price 2500 --purpose present
    ```

2. **監視銘柄の追加/更新 (`prebuy`)**:
    - 指定した銘柄を監視リストに追加または更新します。数量は1株で固定されます。
    - `--watch`オプションでステータスを`監視中`に設定します。
    - `--get`オプションでステータスを`購入検討中`に設定します。
    - `--status`オプションで直接ステータスを指定することも可能です（`--watch`や`--get`が優先されます）。
    - `--purpose`オプションで目的を指定できます。

    ```bash
    # 監視中に追加
    python3 -m python.trading.buy_and_sell_stock prebuy 9434.T --watch --price 200 --purpose long
    # 購入検討中に追加
    python3 -m python.trading.buy_and_sell_stock prebuy 9434.T --get --price 200 --purpose middle
    # ステータスを直接指定
    python3 -m python.trading.buy_and_sell_stock prebuy 9434.T --status "除外" --price 200
    ```

3. **株の売却 (`sell`)**:
    - 指定した銘柄を数量売却し、`my_stock.csv`を更新します。
    - 保有数が0になった場合、`my_stock.csv`から該当行を削除します。
    - `--profit_loss_status`オプションで売却ステータス（`売却済（利益確定）`, `売却済（損切り）`）を指定できます。

    ```bash
    python3 -m python.trading.buy_and_sell_stock sell 6758.T 5 --profit_loss_status 売却済（利益確定）
    ```

4. **CSVの更新とクリーンアップ (`refresh`)**:
    - `my_stock.csv`の現在価格、損益などを更新します。
    - `my_stock.csv`に`sector`カラムが存在し`purpose`カラムが存在しない場合、`sector`を`purpose`に自動リネームします。
    - `quantity`が0で、かつ`status`が`売却済（利益確定）`, `売却済（損切り）`, `除外`以外の行、または無効な`status`を持つ行をCSVから削除します。

    ```bash
    python3 -m python.trading.buy_and_sell_stock refresh
    ```

5. **CSV形式チェック (`csv-check`)**:
    - `my_stock.csv`の基本的な形式が正しいかチェックします。

    ```bash
    python3 -m python.trading.buy_and_sell_stock csv-check
    ```

6. **CSVの対話形式編集 (`csv-edit`)**:
    - 指定した銘柄の`status`または`purpose`を対話形式で変更します。

    ```bash
    python3 -m python.trading.buy_and_sell_stock csv-edit 9434.T
    ```

    実行後、現在のステータスと目的が表示され、変更する項目を選択するプロンプトが表示されます。

7. **過去の取引履歴の追加 (`add_transaction`)**:
    - 過去の取引履歴をデータベースの`transactions`テーブルに記録します。

    ```bash
    # 購入履歴を追加
    python3 -m python.trading.buy_and_sell_stock add_transaction 9434.T buy 10 220.5 2025-01-15
    # 売却履歴を追加
    python3 -m python.trading.buy_and_sell_stock add_transaction 9434.T sell 5 230.0 2025-03-20
    ```

## データベーススキーマの更新について

今回の機能追加に伴い、データベースのスキーマ変更が必要です。
`python/init_database.py`を実行することで、既存のデータは保持されたまま、必要なカラム名の変更（`sector` -> `purpose`）と`transactions`テーブルの作成が行われます。

```bash
python3 -m python.init_database
