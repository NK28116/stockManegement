# Goal to Deploy

## フェーズ0：前提整理（必須）

### 0-1. デプロイ形態の最終決定

* [ ] **WebUI：Cloud Run**
* [ ] **定期実行：GCE（既存）**
* [ ] **永続ストレージ：GCS**

※ ここでは「GCEは既にある前提」で進めます。

---

## フェーズ1：ルール管理の確定（最重要）

### 1-1. trading_rules.json の正式スキーマ確定

* [x] version フィールド追加
* [x] 有効/無効フラグ
* [x] 数値の単位・許容範囲定義
* [x] UI ↔ JSON ↔ Python の完全一致

例（最終形）：

```json
{
  "version": "1.0.0",
  "updated_at": "2025-12-14T13:20:00Z",
  "active": true,
  "risk": {
    "stop_loss_percent": 0.05,
    "take_profit_percent": 0.1,
    "trailing_stop_percent": 0.03,
    "risk_per_trade": 0.01,
    "max_loss_percent": 0.03
  },
  "indicators": {
    "rsi": {
      "overbought": 70,
      "oversold": 30
    },
    "macd": {
      "fast": 12,
      "slow": 26,
      "signal": 9
    },
    "bollinger": {
      "period": 20,
      "std": 2
    }
  }
}
```

---

### 1-2. Python 側の完全対応

* [x] `TradingRules` schema が上記構造を読む
* [x] `ImprovedTradingRules.__init__` が JSON を直接受け取れる
* [x] config.py フォールバック確認

---

### 1-3. ルール履歴管理

* [x] `trading_rules/active.json`
* [x] `trading_rules/history/YYYYMMDD_HHMMSS.json`
* [x] WebUI保存時に **必ず履歴保存**

---

## フェーズ2：GCS 設計・実装

### 2-1. GCS バケット作成

* [x] `stock-management-prod`（1バケットで十分）

---

### 2-2. ディレクトリ構造反映

```text
gs://stock-management-prod/
├── trading_rules/
│   ├── active.json
│   └── history/
├── market_data/
│   └── daily/
├── charts/
│   ├── indicators/
│   └── signals/
├── reports/
│   ├── daily/
│   └── monthly/
└── logs/
```

* [x] ディレクトリ作成完了（gsutil ls で確認済み）

---

### 2-3. ローカル → GCS 複製

デバッグのためlocalは残す

* [x] active.json → `trading_rules/`
* [x] chartImg → `charts/`
* [x] report → `reports/`
* [x] data 保存先を **GCSに切替**
  * [x] `python/utils/gcs_client.py` 実装（GCS/Local 同時書き込み or 切り替え）
  * [x] `rules_loader.py` を GCS 対応
  * [x] `charts.py` を GCS 対応（画像参照先変更）

---

## フェーズ3：WebUI（Cloud Run）デプロイ準備

### 3-1. app.py の責務分離

* [ ] WebUI は「読む・書く」だけ
* [ ] 分析ロジックを一切持たない

---

### 3-2. GCS I/O 実装

* [x] rules の GET/POST が GCS 直結
* [x] charts は署名URL or public read (or backend proxy)

---

### 3-3. Dockerfile 作成

* [x] Base Image: `python:3.12-slim`
* [x] Requirements: `fastapi`, `uvicorn`, `google-cloud-storage`, `jinja2`, `python-multipart`
* [x] Entrypoint: `uvicorn python.web.app:app --host 0.0.0.0 --port $PORT`
* [x] `gunicorn` は今回は `uvicorn` 単体でも可（Cloud Run は前段にLBがいるため）

---

### 3-4. Cloud Run 設定 (コマンドラインで実行予定)

* [x] `gcloud builds submit --tag gcr.io/stockmanagement-gce/stock-web-ui`
* [x] `gcloud run deploy stock-web-ui --image gcr.io/stockmanagement-gce/stock-web-ui --allow-unauthenticated`
    * Region: `us-east1` (Always Free)
    * URL: `https://stock-web-ui-664052483309.us-east1.run.app`
* [x] 環境変数設定:
  * [x] `GCS_BUCKET_NAME=stock-management-prod`
  * [x] `GOOGLE_CLOUD_PROJECT=stockmanagement-gce`

### 3-5. CI/CD (GitHub Actions)

* [x] Workflow設定: `.github/workflows/google-cloudrun-docker.yml` (WIF + gcr.io)
* [x] IAM & Secrets設定:
  1. `scripts/setup_wif.sh` を実行
  2. GitHub Repository Settings > Secrets and variables > Actions に以下を設定:
     * `GCP_PROJECT_ID`
     * `GCP_WIF_PROVIDER`
     * `GCP_SERVICE_ACCOUNT`

---

## 4. 運用監視 (Phase 4)

：定期実行（自動監視）

### 4-1. 実行方式決定

* [x] GCE cron（既存）

---

### 4-2. 実行時フロー整理

* [x] GCS から `active.json` 読む
* [x] 指標計算
  - データ構造の考察
  - [x] PostgreSQLデータベースを使用 (GCE上のDocker)
    - Tables: `stocks`, `daily_prices`, `signals`, `trade_history`
  - [x] ORM: SQLAlchemy + Alembic (マイグレーション管理)
* [x] ルールを変更するかどうかを考察
  * **採用基準案**:
    * **Profit Factor**: 直近3ヶ月で `1.2` 未満
    * **Max Drawdown**: `15%` 超過
    * **勝率**: `35%` 未満 (リスクリワード依存)
    * **連敗数**: `6` 連敗以上
  * [ ] 基準から乖離したものを検出した場合にルール変更を提案
  * [ ] ルール変更の自動化はしない（必ず人が確認する）
* [x] ルールを変更理由をプルダウンか何かで選択できるようにする
  - [x] `TradingRules` schema に `change_reason` フィールド追加
  - [x] WebUI 保存時に理由入力モーダルを表示
    * **候補案**:
      * `Performance Optimization` (パフォーマンス最適化)
      * `Risk Mitigation` (リスク軽減)
      * `Market Regime Change` (相場環境変化)
      * `Logic Correction` (ロジック修正)
      * `Regular Update` (定期更新)
      * `Testing` (テスト・実験)
  - [x] WebUI にプルダウンメニューを追加
* [x] charts 出力 → GCS
* [x] シグナル判定
* [x] 株価を手動更新して指標計算をする( 1度更新したら1時間は更新できない等の制限をつける )


### 4-3. 冪等性確認

* [x] 同日複数回実行NG
* [ ] 日時別保存

---

## フェーズ5：セキュリティ・運用最低限

### 5-1. 認証情報整理

* [ ] APIキーは Secret Manager
* [ ] コード内の `KEY.json` 参照を廃止し `google-cloud-secret-manager` 経由に変更

---

### 5-2. IAM

* [ ] Cloud Run → GCS read/write
* [ ] cron 実行用 SA 限定権限

---

### 5-3. ログ

* [ ] Cloud Logging 有効
* [ ] 異常検知ログ

### 5-4. 運用に必要なUI，ロジックの追加

* [ ] UIの改善
  - ステータス，目的ごとにソート，フィルタできるようにする
  - 収益の合計を表示する

* [ ] 株を追加するロジックやUIを追加

---

## フェーズ6：本番前チェック（必須）

### 6-1. ローカル → ステージング

* [ ] Cloud Run にデプロイ（非公開）
* [ ] 実データで一巡

---

### 6-2. ドライラン

* [ ] ルール変更 → 即反映確認
* [ ] charts 更新確認
* [ ] 通知確認

---

### 6-3. ロールバック確認

* [ ] 過去ルール復元
* [ ] active.json 差し替え

---

## フェーズ7：本番運用開始

* [ ] Privateな情報を削除
* [ ] READMEを含めたDocsの編集などのOSS公開準備
  - 各ディレクトリにあるREADMEも更新する
* [ ] WebUI 公開（制限付き）
* [ ] cron 有効化
* [ ] 監視開始

## フェーズ8：将来拡張検討

Docs/WayToBenefit.mdを参考に、以下の拡張を検討

* [ ] 高度ルール追加
* [ ] 証券会社APIなどの他ツールとの連携
* [ ] 監視市場の追加 <- 収益化可能性
* [ ] 英語圏に対応 <- 収益化可能性
* [ ] Slack 通知
  - [ ] 通知フィルタクラスの実装 (`NotificationManager`)
    - 前回通知したシグナルと比較し、状態変化(Buy->Sell等)のみ通知
    - 損切りライン到達は即時通知
    - 定期的な「異常なし」通知は廃止
* [ ] 通知ツールの追加（LINE, Discordなど）
* [ ] レスポンシブデザイン対応
* [ ] 
