# Claudeへの実装指示書：週足スイングトレード分析機能の実装

本ドキュメントは、`Docs/design.md` (設計書) に基づき、保有・監視銘柄に対する週足スイングトレード分析機能を実装するための指示書です。

**目的**: バックエンドでテクニカル分析を実行し、売買シグナルを生成・保存・表示する一連の機能を実装すること。

---

## 0. 関連ディレクトリ・ファイルとライブラリ (Reference)

実装にあたっては、以下の既存ロジックおよびライブラリを最大限活用してください。

- **テクニカル指標計算ロジック**:
    - `python/utils/indicators.py`: 移動平均 (MA), RSI, MACD 等の基本計算。
    - `python/analysis/formula_for_analyzer.py`: `ta` ライブラリを用いた指標計算の実装例。
- **使用ライブラリ**:
    - `ta`: ボラティリティ（ATR等）、トレンド、モメンタム指標の計算に使用（既にプロジェクトに導入済み）。
- **設定値**:
    - `python/config.py`: 各種閾値やパラメータの管理。

---

## 1. データベース実装 (Priority: High)

### 1.1 モデル定義
**対象ファイル**: `python/db/models.py` (または適切なモデル定義ファイル)
- 以下の `Signal` モデル (テーブル名: `signals`) を定義してください。
    - `id`: Integer, Primary Key
    - `symbol`: String, 銘柄コード (Index)
    - `analysis_date`: Date, 分析実行日
    - `signal_type`: String, ('LONG', 'SHORT', 'NONE')
    - `score`: Integer, 総合スコア
    - `detected_patterns`: String (JSON形式で保存), 検出パターンリスト
    - `stop_loss`: Float, 損切り価格
    - `take_profit`: Float, 利確目標価格
    - `rationale`: Text, 判定根拠サマリ
    - `created_at`: DateTime, 作成日時 (default=now)

### 1.2 マイグレーション
- `alembic` を使用してマイグレーションスクリプトを作成し、DBに適用してください。

---

## 2. バックエンド分析ロジック実装 (Priority: High)

### 2.1 分析エンジン実装
**対象ファイル**: `python/watch/analyze.py`
- `main()` 関数および以下のヘルパー関数群を実装してください。
- **データ取得**: 登録銘柄の週足データを取得するロジック。
- **環境認識 (`environment_filter`)**:
    - 40週移動平均線 (40MA) を計算。
    - ※ 既存の移動平均計算ロジック (`python/utils/indicators.py` または `python/analysis/formula_for_analyzer.py`) を参照・利用すること。
    - 判定:
        - **Long**: 終値 > 40MA AND 40MAスロープ > 0
        - **Short**: 終値 < 40MA AND 40MAスロープ < 0
- **パターン検出 (`detect_patterns`)**:
    - ダブルボトム、逆三尊、フラッグ、トライアングル等を識別するロジック（簡易的でも可、拡張性を持たせる）。
    - 出来高増加（vs 20週平均）の判定。
- **リスク管理 (`calculate_risk`)**:
    - ATR(14) を計算。
    - ※ `ta` ライブラリ (`ta.volatility.AverageTrueRange`) を利用して計算すること（`python/analysis/formula_for_analyzer.py` で既に使用例あり）。
    - Stop Loss = Entry +/- (ATR * 1.5)
    - Take Profit = Entry +/- (ATR * 1.5 * 2.0) (RR 1:2)
- **スコアリング (`score_pattern`)**:
    - トレンド一致(+3), パターン完成(+3), 出来高増(+2), RSI適正(+1), RR良(+1) で加点。
    - 合計8点以上を有効シグナルとする。

### 2.2 単体テスト
**対象ファイル**: `tests/test_analyze_logic.py` (新規作成)
- 各ロジック関数（トレンド判定、パターン検出、リスク計算）に対する単体テストを作成してください。

---

## 3. API実装 (Priority: Medium)

### 3.1 エンドポイント追加
**対象ファイル**: `main.py` (FastAPIアプリケーション)
- **POST /api/analyze**:
    - 分析タスクをバックグラウンド（`BackgroundTasks`）で起動。
    - 即座に `202 Accepted` を返す。
- **GET /api/signals/latest**:
    - `signals` テーブルから最新の分析結果を取得してJSONで返す。
    - レスポンス形式: `[{"symbol": "7203", "signal_type": "LONG", "score": 9, ...}, ...]`

---

## 4. フロントエンド実装 (Priority: Medium)

### 4.1 UI更新
**対象ファイル**: `index.html` / `static/js/app.js` (または該当するJSファイル)
- **Check Signal ボタン**:
    - ID: `check-signal-btn`
    - クリック時に `POST /api/analyze` をfetch。
    - Loading表示の実装（ボタンの無効化、スピナー表示）。
- **結果表示エリア**:
    - ID: `signal-results`
    - `GET /api/signals/latest` の結果をテーブル表示。
    - カラム: 銘柄コード、シグナル(Long/Short)、スコア、推奨アクション。
    - 高スコア（8点以上）の行をハイライト。

---

## 5. 補足・制約
- 重い分析処理は非同期（バックグラウンド）で行い、APIレスポンスを2秒以内に保つこと。
- コードはモジュール化し、将来的なルールの変更（MA期間の変更など）に対応しやすくすること。
- エラーハンドリングを適切に行い、分析失敗時もサーバーが停止しないようにすること。