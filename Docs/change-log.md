# 変更ログ

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
