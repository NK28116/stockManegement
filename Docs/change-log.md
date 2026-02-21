# 変更ログ

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
