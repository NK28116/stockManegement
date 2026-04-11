# 変更ログ

## 2026-02-22 (ユーザーレビューに基づくUI・DB連動改善)

### 概要
ユーザーからの3点のフィードバック（Check Signals安全化、Sell/Deleteトースト改善、ローカルCSV連動徹底）に対応する改善を実施。

### 詳細

#### 1. Check Signals ボタン安全化 (`python/web/api/signals.py`)
- `_run_swing_analysis` 関数の先頭に `init_db()` を追加し、`signals` / `signal_history` テーブルが未作成でもエラーにならないよう保護

#### 2. Sell/Delete トースト表示改善 (`python/web/templates/index.html`)
- `sellStock()` の完了通知を `alert()` からトースト通知 (`toastMessage`) に変更
- `deleteStock()` と `sellStock()` 双方で `await this.fetchCharts()` の完了後にトーストをセットするよう順序を修正。これによりDOMの再描画でトーストが消えるのを防止
- エラー時もトースト通知に統一

#### 3. ローカルCSV連動の徹底
- `config.py`: `default_portfolio_file` が `my_stock.csv` にハードコーディングされていたのを `_csv_filename`（DB_ENV依存）に修正
- `charts.py`: GCSフォールバックのパスを `data/my_stock.csv` から `config.codes_path` に修正し、`config` をインポート追加

---

## 2026-02-22 (Updateボタン: ローカルCSVの `last_updated` 更新対応)

### 概要
ダッシュボードの「Update」ボタン（市場データ更新）をクリックした際、バックグラウンド処理完了後に対象CSVファイル（ローカル環境では `data/my_stock_local.csv`）の全銘柄の `last_updated` カラムを現在のシステム日時に一括更新するようにした。

### 詳細

#### 1. バックグラウンド更新処理の拡張 (`python/web/routes/actions.py`)
- `_run_market_update()` 関数内で `watch.main()` 完了後に CSV更新処理を追加
- `buy_and_sell_stock.load_codes` / `save_codes` を使用し、`config.codes_path` のCSVファイルを読み書き
- `last_updated` カラム全体を `YYYY/MM/DD HH:MM:SS` フォーマットの現在日時で上書き
- CSV更新のエラーは独立した `try-except` で囲み、メインのバックグラウンド処理に影響しない設計

---

## 2026-02-22 (ダッシュボード「幽霊銘柄」問題の修正 / Log4対応)

### 概要
削除済みの銘柄がダッシュボード上に再表示され、再度削除しようとすると `404 Not Found` エラーになる問題を修正した。

### 詳細

#### 1. 表示対象のフィルタリング追加 (`python/web/routes/charts.py`)
- `/api/charts/list` のレスポンス生成ロジックにフィルタリングを追加
- 従来は画像ファイルの存在のみを基準にリスト生成していたため、CSVから削除済みの銘柄でもチャート画像が残っている限りダッシュボードに表示されていた
- 修正後は、CSVのポートフォリオデータ (`stock_data`) に存在する銘柄のみをレスポンスに含めるようフィルタリング
- これにより削除済み銘柄の「幽霊」表示が解消され、二重削除時の `404 Not Found` エラーが物理的に発生しなくなった

---

## 2026-02-22 (UIトースト延長・参照CSV環境分離)

### 概要
ユーザーレビューに基づき、トースト通知を十分な時間表示するよう延長し、ローカル開発時とクラウド環境で参照するCSVファイルを自動的に切り替える機能を実装した。

### 詳細

#### 1. トースト表示時間の延長 (`python/web/templates/index.html`)
- 売却・削除成功トーストの `setTimeout` を **3000ms → 7000ms** に延長
- 削除エラートーストの `setTimeout` を **5000ms → 7000ms** に延長
- ルール保存成功メッセージの `setTimeout` を **3000ms → 7000ms** に延長
- これによりユーザーが操作結果を確実に視認できるようになった

#### 2. 参照CSVの環境分離 (`python/config.py`)
- `__init__` の処理順序を修正し、`db_env` を `codes_path` より先に読み込むよう変更
- `DB_ENV=local` (ローカル開発時): `data/my_stock_local.csv` を参照
- `DB_ENV=cloud` (GCE/ステージング時): `data/my_stock.csv` を参照
- `config.codes_path` を参照するすべてのバックエンド処理（`sell_stock`, `delete_stock`, `sync_csv_to_portfolio` 等）が自動的に環境に適したCSVへ切り替わる
- `.env` に `export DB_ENV="local"` と設定されているため、ローカル起動時は即座に `my_stock_local.csv` が使用される

---

## 2026-02-22 (PostgreSQL portfolio テーブル自動同期実装)

### 概要
CSVファイル (`my_stock.csv`) と PostgreSQLの `portfolio` テーブルが常に同期されるようにした。
アプリ起動時の自動同期と、売却・削除アクション時の即時反映を実装。

### 詳細

#### 1. 同期関数追加 (`python/db/database.py`)
- `sync_csv_to_portfolio()` 関数を新規追加
  - `config.codes_path` のCSVを読み込み、全量を portfolio テーブルへ Upsert する
  - `profit_loss_percent` に混入した `%` 文字列を自動除去（PostgreSQL Numeric型エラー対策）
  - NaN値は NULL に変換して型安全を確保
- `delete_portfolio_record(code)` 関数を新規追加
  - 指定銘柄コードの portfolio レコードを DB から削除する
- `update_portfolio_status(code, status, quantity)` 関数を新規追加
  - 売却時に portfolio レコードのステータス・数量を更新する
- `sqlalchemy.delete` / `sqlalchemy.update` を import に追加

#### 2. アプリ起動時の自動同期 (`python/web/app.py`)
- `lifespan` 関数を更新
  - PostgreSQLモード（デフォルト）では起動時に `sync_csv_to_portfolio()` を自動実行
  - SQLiteモードは従来通り `init_db()` でテーブル作成のみ
  - 同期エラーが発生してもアプリ起動は継続（WARNING ログのみ）

#### 3. 売却・削除アクション時のDB同期 (`python/trading/buy_and_sell_stock.py`)
- `sell_stock()` の末尾に `update_portfolio_status()` 呼び出しを追加
  - CSV更新後、DBの該当レコードのステータスと数量も即時更新
- `delete_stock()` の末尾に `delete_portfolio_record()` 呼び出しを追加
  - CSV行削除後、DBの該当レコードも即時削除
  - いずれもDB処理失敗はwarnログに留め、メインのCSV処理は影響しない設計

---

## 2026-02-22 (ダッシュボードから削除ボタン追加)

### 概要
ダッシュボードの各銘柄リスト行に「🗑️ 削除」ボタンを追加し、CSVから銘柄を完全に削除できるようにした。

### 詳細

#### 1. 削除ロジック追加 (`python/trading/buy_and_sell_stock.py`)
- `delete_stock(code)` 関数を新規追加
  - `load_codes()` → 対象code行を `df.drop()` → `save_codes()` の流れでCSVから完全削除
  - 存在しないコードが指定された場合は `{"error": ...}` を返す

#### 2. APIエンドポイント追加 (`python/web/routes/actions.py`)
- `DELETE /api/actions/stock/{code}` エンドポイントを新規追加
  - `buy_and_sell_stock.delete_stock()` を呼び出し
  - 成功時: `{"status": "success", "message": "..."}`
  - 銘柄未存在時: `404` エラー

#### 3. フロントエンド更新 (`python/web/templates/index.html`)
- ダッシュボードテーブルの各行に **🗑️ 削除** ボタンを追加（既存Sellボタンの横）
  - `confirm()` で「本当に削除しますか？」確認ダイアログを表示
  - API呼び出し中はボタンを無効化し「削除中...」表示
  - 成功時: トースト通知で「〇〇をダッシュボードから削除しました」を表示、リスト自動更新
  - エラー時: トースト通知でエラーメッセージを表示
- `deletingCode` データプロパティを追加（処理中表示制御用）

---

## 2026-02-22 (改訂版3 追補)

### 概要
SQLiteモード時の `signals` テーブル未作成エラーを修正

### 詳細

#### 1. テーブル自動作成 (`python/db/database.py`) [Section 2.5 / Priority: Critical]
- 全モデルのインポートを追加: `Signal`, `SignalHistory`, `Stock`, `DailyPrice`
  - `Base.metadata.create_all()` が全テーブルを認識できるようにした
- SQLiteエンジン作成直後に `Base.metadata.create_all(bind=engine)` を自動実行
  - `signals` テーブルが存在しない (`no such table: signals`) エラーを解消

#### 2. 起動時テーブル保証 (`python/web/app.py`) [Section 2.5]
- FastAPI `lifespan` イベントハンドラを追加
  - `DB_TYPE=sqlite` の場合、アプリ起動時に `init_db()` を呼び出しテーブル存在を二重保証

---

## 2026-02-22 (改訂版3)

### 概要
DB接続バグ修正・SQLite対応・紫ボタンへのswing analysis統合

### 詳細

#### 1. DB接続の修正と柔軟化 (`python/db/database.py`) [Section 2.4]
- **バグ修正**: `db_conf.get('dbname', ...)` → `db_conf.get('database', ...)` に修正
  - `config.py` の `get_db_config()` が返すキー名と整合
- **SQLite対応**: `DB_TYPE=sqlite` 環境変数でローカル SQLite に切り替え可能
  - `SQLITE_PATH` 環境変数でパス指定可能（デフォルト: プロジェクトルート `test_stock.db`）
  - SQLite の場合 `connect_args={"check_same_thread": False}` を設定
  - `upsert_portfolio_data` を DB 種別に応じて `sqlite.insert` / `postgresql.insert` で分岐

#### 2. 紫ボタンへのSwing Analysis統合 (`python/web/templates/index.html`) [Section 3.1]
- **`triggerAnalysis()`** を `/api/signals/analyze` を呼び出す実装に更新
  - `alert()` をトースト通知に置換
  - 分析完了まで `_startPolling()` によるポーリングを実行
  - `swingAnalyzing` フラグでローディングスピナー・ボタン無効化を制御
- **ボタンの disabled 条件**を `actionStatus.is_analyzing || swingAnalyzing` に更新
  - swing分析中はスピナー付きの「Analyzing...」表示
- **Signals タブのボタン**を削除し、ヘッダーの紫ボタンへの案内文に統一
- **`_startPolling()`** に二重起動防止ガードを追加

## 2026-02-21 (改訂版2)

### 概要
ローカル環境検証準備・ログ強化・UI実行フィードバック改善・DISTINCT ON バグ修正

### 詳細

#### 0. バグ修正 (`python/web/api/signals.py`) [Section 2.3 / Priority: Critical]
- `GET /api/signals/latest` の SQL クエリを `DISTINCT ON`（PostgreSQL 固有）から標準 SQL に書き換え
  - 旧: `DISTINCT ON (symbol) ... ORDER BY symbol, created_at DESC`
  - 新: `JOIN (SELECT symbol, MAX(created_at) AS max_created_at FROM signals GROUP BY symbol) t2 ON ...`
  - ローカル SQLite 環境で発生していた `500 Internal Server Error` を解消

#### 1. DB同期スクリプト作成 (`scripts/sync_local_db.py`) [Section 1.1]
- `data/my_stock_local.csv` の内容を `test_stock.db` (SQLite) へ同期するスクリプトを新規作成
- `stocks` および `portfolio` テーブルを自動作成（存在しない場合）
- `INSERT ... ON CONFLICT DO UPDATE` で冪等な upsert を実現
- `--csv` / `--db` オプションでパス指定可能（デフォルトはプロジェクトルート基準）

#### 2. 分析ログ強化 (`python/watch/analyze.py`) [Section 2.2]
- `main()`: 銘柄数ログを追加 → `分析対象銘柄数: N`
- `_analyze_weekly_swing()`:
  - データが空の場合と件数不足の場合のログを分離し、取得行数・必要行数を明記
  - データ取得成功時に取得行数をログ出力
  - スコアログに閾値比較結果を追加 → `score=N/8 [有効シグナル|閾値未達(閾値=8)]`

#### 3. ステータスAPIエンドポイント追加 (`python/web/api/signals.py`)
- `GET /api/signals/status` を追加 → `{"is_analyzing": bool}` を返す
- フロントエンドのポーリングから分析完了を検知するために使用

#### 4. UI実行フィードバック強化 (`python/web/templates/index.html`) [Section 3.1]
- **トースト通知を実装**:
  - 画面右上に固定表示する通知コンポーネントを追加（`toastMessage` / `toastType`）
  - `alert()` を全廃し、`showToast()` メソッドに置き換え
  - 6秒後に自動消去、✕ボタンで手動消去
- **分析完了ポーリングを実装**:
  - `_startPolling()`: 15秒間隔でステータスAPIをポーリング、最大6分
  - `is_analyzing` が false になったタイミングで結果を再取得
  - 0件: 「分析完了：新しいシグナルはありませんでした」、N件: 「分析完了：N件のシグナルが検出されました」
  - `_stopPolling()`: インターバルを適切にクリア

## 2026-02-21 (改訂版)

### 概要
週足スイングトレード分析機能の改訂実装（ユーザーレビュー対応）

### 詳細

#### 1. レートリミット対策 (`python/watch/analyze.py`)
- `main()` のループ内で銘柄ごとに `time.sleep(1)` を追加
- yfinance API への連続リクエストによるレート制限エラーを回避

#### 2. `is_held` フィールド追加 (`python/web/api/signals.py`)
- `SignalResponse` モデルに `is_held: bool` を追加
- `GET /api/signals/latest` のクエリを `portfolio` テーブルと LEFT JOIN するよう変更
  - 未売却ステータスの銘柄コードと一致する場合に `is_held = true` をセット
  - 対象外ステータス: `SOLD_PROFIT`, `SOLD_LOSS`, `売却（利益確定）`, `売却（損切り）`

#### 3. UI 視認性向上 (`python/web/templates/index.html`)
- **行の色分けロジックを改訂**（優先順位順）:
  - 保有中かつ SHORT シグナル → ピンク (`#ffc0cb`)
  - LONG シグナル（保有・未保有問わず） → 青 (`#add8e6`)
  - それ以外でスコア 8 点以上 → 黄 (`#fefce8`)
- **詳細モーダルを実装**:
  - 行クリックで `openSignalDetail()` を呼び出し
  - モーダル内容: シグナル種別・スコア・推奨アクション・損切り・利確目標・検出パターン・判定根拠テキスト
- **保有中バッジ** (`保有中` ラベル) を銘柄コード列に追加
- **色凡例** をテーブル下部に追加

## 2026-02-21

### 概要
週足スイングトレード分析機能を実装

### 詳細

#### 1. DB モデル追加 (`python/db/models.py`)
- `Signal` モデル（テーブル名: `signals`）を新規追加
  - `id`, `symbol`, `analysis_date`, `signal_type`, `score`, `detected_patterns`, `stop_loss`, `take_profit`, `rationale`, `created_at` 各カラム

#### 2. Alembic マイグレーション作成
- `alembic/versions/0001_create_signals_table.py` を新規作成
  - `signals` テーブル作成 / `symbol` インデックス作成の up/down 定義

#### 3. 分析エンジン実装 (`python/watch/analyze.py`)
- `main()` を週足スイング分析のエントリーポイントとして実装
- 追加した関数:
  - `get_weekly_price_data(symbol)` — yfinance で週足 OHLCV 取得
  - `environment_filter(df)` — 40週移動平均でトレンド方向判定（LONG/SHORT/NONE）
  - `detect_patterns(df)` — ダブルボトム・逆三尊・フラッグ・トライアングル・出来高増加を検出
  - `calculate_risk(df, trend)` — `ta.volatility.AverageTrueRange` を用いた ATR(14) ベースのストップロス・利確目標計算（Stop: ATR×1.5、TP: ATR×3.0 → RR 1:2）
  - `score_pattern(trend, patterns, df, risk)` — トレンド一致(+3)・パターン完成(+3)・出来高増加(+2)・RSI適正(+1)・RR良好(+1) でスコアリング。8点以上を有効シグナルとして DB 保存

#### 4. API エンドポイント追加 (`python/web/api/signals.py`)
- `POST /api/signals/analyze` — 週足スイング分析をバックグラウンドで起動、即時 202 Accepted を返す
- `GET /api/signals/latest` — `signals` テーブルから銘柄ごとの最新シグナルを取得して JSON 返却

#### 5. フロントエンド更新 (`python/web/templates/index.html`)
- 「Signals」タブを追加
  - `id="check-signal-btn"` の「Check Signal」ボタン（クリックで `POST /api/signals/analyze` をfetch、ローディングスピナー付き）
  - `id="signal-results"` の結果表示テーブル（銘柄コード・シグナル・スコア・推奨アクション・損切り・利確目標・分析日）
  - スコア 8 点以上の行を黄色ハイライト表示

#### 6. 単体テスト追加 (`tests/test_analyze_logic.py`)
- 25 テストケースを新規作成、全テスト通過 (25/25 passed)
  - `TestEnvironmentFilter` — トレンド判定ロジック（上昇/下降/データ不足/フラット）
  - `TestDetectPatterns` — パターン検出（出来高増加・データ不足・戻り値型）
  - `TestCalculateRisk` — リスク計算（キー確認・LONG/SHORT の価格方向・RR 比率）
  - `TestScorePattern` — スコアリング（各加点条件の独立検証）
  - `TestLinearSlope` — 線形スロープ計算（正/負/ゼロ/1要素）
