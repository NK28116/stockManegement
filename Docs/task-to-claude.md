# Claudeへの実装指示書：週足スイングトレード分析機能の実装（改訂版3）

本ドキュメントは、`Docs/design.md`、`Docs/review.md`、ユーザーからの不具合報告およびUI改善要望に基づき、週足スイングトレード分析機能の実装と、ローカル環境での検証手順を定義するものです。

**目的**: バックエンド分析機能の実装を完了させ、ローカル環境 (`localhost:8888`) で `data/my_stock_local.csv` のデータを用いて正常に動作することを確認する。また、既存UIとの調和を図る。

---

## 0. 関連ディレクトリ・ファイルとライブラリ (Reference)

- **テクニカル指標計算**: `python/utils/indicators.py`, `python/analysis/formula_for_analyzer.py`, `ta` ライブラリ。
- **データソース**: `data/my_stock_local.csv` (ローカル検証用), `data/my_stock.csv` (本番用)。
- **分析エンジン**: `python/watch/analyze.py`。

---

## 1. ローカル環境検証の準備 (Priority: High)

ユーザーがローカルで動作確認を行えるよう、以下の手順・機能を実装してください。

### 1.1 DB同期スクリプトの作成・整備
- **タスク**: `data/my_stock_local.csv` の内容をローカルデータベース (`test_stock.db` 等) の `stocks` および `portfolio_holdings` テーブルに同期するコマンドまたはスクリプトを整備してください。
- **目的**: 分析対象となる銘柄データがDBに存在しないために分析がスキップされるのを防ぎます。

### 1.2 ダミーデータの投入 (検証用)
- 必要に応じて、`daily_data` テーブルに直近数週間分の週足データ（または日足から集計可能なデータ）が存在することを確認する、あるいは yfinance からの取得が確実に動作する銘柄（例: `7203.T`）が `my_stock_local.csv` に含まれていることを確認してください。

---

## 2. バックエンド実装の修正・強化 (Priority: High)

### 2.1 エンドポイントの一致確認
- **対象**: `python/web/api/signals.py` および `python/web/app.py`
- **確認**: フロントエンドが fetch する URL (`/api/signals/analyze`) と、バックエンドで定義されているルートが完全に一致していることを確認してください。

### 2.2 分析処理のログ出力強化
- `python/watch/analyze.py` 内で、以下のポイントに詳細なログ (`logger.info`) を追加してください。
    - 分析開始時の銘柄数。
    - 各銘柄のデータ取得成否。
    - スコア算出結果（8点未満でもログには出す）。
    - DBへの保存完了通知。

### 2.3 バグ修正 (Priority: Critical)
- **対象**: `python/web/api/signals.py` (`get_latest_signals` 関数)
- **問題**: `DISTINCT ON` 構文は PostgreSQL 固有であり、SQLite (ローカル環境) では `500 Internal Server Error` を引き起こす可能性があります。
- **修正**: 標準 SQL (ウィンドウ関数 `ROW_NUMBER()` または `GROUP BY` + `MAX()`) を用いたクエリに書き換えてください。

### 2.4 DB接続の柔軟化とバグ修正 (Priority: High)
- **対象**: `python/db/database.py`
- **修正1 (キー名の不一致)**: `db_conf.get('dbname', 'stock_db')` を `db_conf.get('database', 'stock_db')` に修正し、`config.py` との整合性を取ってください。
- **修正2 (SQLite対応)**: 環境変数 `DB_TYPE=sqlite` または `DB_ENV=local` かつ特定の条件下で `sqlite:///test_stock.db` を使用するように `DATABASE_URL` の構築ロジックを修正してください。
    - ローカル環境での検証を容易にするため、`psycopg2` がインストールされていない、あるいは PostgreSQL が起動していない環境でも SQLite で動作するようにします。

### 2.5 データベースの初期化・テーブル作成 (Priority: Critical)
- **対象**: `python/db/database.py` および起動時処理 (`main.py` 等)
- **問題**: DB接続をSQLiteに切り替えた際、`signals` テーブルが存在しない (`no such table: signals`) ため、分析結果の保存および取得時にエラーが発生しています。
- **修正**: アプリケーション起動時（あるいは `init_db()` などの初期設定処理内）で、`Base.metadata.create_all(bind=engine)` を実行し、必要なテーブル（特に `signals` テーブル）が自動的に作成されるように実装を追加してください（Alembicを利用している場合は、SQLite環境向けにマイグレーションが実行される仕組みを整備してください）。

---

## 3. フロントエンド UI/UX の改善 (Priority: High)

### 3.1 既存ボタンへの機能統合 (ユーザー要望対応)
- **対象**: `index.html` (Vue.js)
- **要望**: 既存の紫色のボタン（`bg-purple-600` / `rgb(147 51 234)`）である「Check Signal」ボタンに、今回実装した分析機能を統合してください。
- **実装**:
    - 既存の「Check Signal」ボタンのクリックイベント (`@click`) を、新しい分析開始関数 (`triggerAnalysis` 等) に紐付けるか、既存関数内で API コールを行うように変更してください。
    - ボタンの見た目（紫色）は維持しつつ、ローディング状態（スピナー表示、無効化）を適切に反映させてください。

### 3.2 実行フィードバックの強化
- **対策**:
    - ボタン押下時に「分析を開始しました（バックグラウンドで実行中）」というトースト通知またはメッセージを表示する。
    - 分析完了後、自動的に結果を再取得（ポーリングまたは完了通知の受信）してテーブルを更新する。
    - もし分析結果が 0 件（シグナルなし）だった場合も、「分析完了：新しいシグナルはありませんでした」と明示する。

### 3.3 視認性の更なる向上 (再掲)
- **保有中かつSHORT**: 背景色 `#ffc0cb` (ピンク)。
- **LONG**: 背景色 `#add8e6` (青)。
- **高スコア**: 背景色 `#fefce8` (薄黄)。
- 行クリックでの詳細モーダル表示。

---

## 4. 運用・レートリミット対策 (Priority: Medium)

- `yfinance` へのリクエスト間に `time.sleep(1)` を挿入。
- 個別銘柄のエラーでループを止めない `try-except` 処理の徹底。

---

## 5. 検証手順 (Claudeへの指示)
1. `data/my_stock_local.csv` を読み込み、DBを更新する（SQLite使用）。
2. サーバーを起動し、ブラウザで紫色の「Check Signal」ボタンを押す。
3. サーバーログを確認し、分析が走っているか、APIリクエストが成功しているかを確認する。
4. UIに分析中である旨が表示され、完了後にテーブルが正しく色分けされて更新されることを確認する。
