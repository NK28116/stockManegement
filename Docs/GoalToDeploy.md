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
* [x] Requirements: `fastapi`, `uvicorn`, `google-cloud-storage`, `jinja2`, `python-multipart`, `google-cloud-secret-manager`, `sqlalchemy`, `psycopg2-binary`, `requests`
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
  * データ構造の考察
  * [x] PostgreSQLデータベースを使用 (GCE上のDocker)
    * Tables: `stocks`, `daily_prices`, `signals`, `trade_history`
  * [x] ORM: SQLAlchemy + Alembic (マイグレーション管理)
* [x] ルールを変更するかどうかを考察
  * **採用基準案**:
    * **Profit Factor**: 直近3ヶ月で `1.2` 未満
    * **Max Drawdown**: `15%` 超過
    * **勝率**: `35%` 未満 (リスクリワード依存)
    * **連敗数**: `6` 連敗以上
  * [x] 基準から乖離したものを検出した場合にルール変更を提案
  * [x] ルール変更の自動化はしない（必ず人が確認する）
* [x] ルールを変更理由をプルダウンか何かで選択できるようにする
  * [x] `TradingRules` schema に `change_reason` フィールド追加
  * [x] WebUI 保存時に理由入力モーダルを表示
    * **候補案**:
      * `Performance Optimization` (パフォーマンス最適化)
      * `Risk Mitigation` (リスク軽減)
      * `Market Regime Change` (相場環境変化)
      * `Logic Correction` (ロジック修正)
      * `Regular Update` (定期更新)
      * `Testing` (テスト・実験)
  * [x] WebUI にプルダウンメニューを追加
* [x] charts 出力 → GCS
* [x] シグナル判定
* [x] 株価を手動更新して指標計算をする( 1度更新したら1時間は更新できない等の制限をつける )

### 4-3. 冪等性確認

* [x] 同日複数回実行NG
* [x] 日時別保存

---

## フェーズ5：セキュリティ・運用最低限

### 5-1. 認証情報整理

* [x] APIキーは Secret Manager
* [x] コード内の `KEY.json` 参照を廃止し `google-cloud-secret-manager` 経由に変更

---

### 5-2. IAM

* [ ] Cloud Run → GCS read/write
* [ ] cron 実行用 SA 限定権限

---

### 5-3. ログ

* [ ] Cloud Logging 有効
* [ ] 異常検知ログ

## フェーズ6：本番前チェック（必須）

最低限の動作確認を行う

* 検証対象
  * localhost:8888
    * `uvicorn python.web.app:app --reload --port 8888`
    * 使用するcsvは`data/my_stock_local.csv`
      * 作成した時とメソッドとか変更しているから過不足の可能性
  * Cloud Run
    * `https://stock-web-ui-664052483309.us-east1.run.app`
    * 使用するcsvはGCE上の`data/my_stock.csv`
    * GCSバケット: `stock-management-prod`
      * 同上

### 6-1. 動作確認

* [x] ローカルで動作確認
  * [x] ルール取得・表示
  * [x] charts 表示
* [x] Cloud Run にデプロイ
  * [x] 最新の株価を使用
* [x] 実データで一巡

---

### 6-2. ドライラン

* [x] ルール変更 → 即反映確認
* [x] charts 更新確認
* [x] 通知確認

---

### 6-3. ロールバック確認

* [x] 過去ルール復元
* [x] active.json 差し替え

---

### 6-4. 追加修正

* [x] **`actions.py` のモック実装解除**
  * 現状 `time.sleep` になっている `_run_market_update` 等を、実際の `python.watch` やデータ更新ロジック呼び出しに置き換える。
  * Cloud Run 上で実行する場合、タイムアウトやメモリ制限に注意が必要。
* [x] **Cloud Run からのデータアクセス経路の確立**
  * Web UI (Cloud Run) から GCE 上の PostgreSQL や GCS 上のデータへ正しくアクセスできるか再確認（VPCコネクタやIAM権限）。
  * 特に `actions.py` でロジックを動かす場合、DB接続情報が必要になる。
  * **設定手順メモ**:
    1. **API有効化**: `gcloud services enable vpcaccess.googleapis.com`
    2. **コネクタ作成**: `gcloud compute networks vpc-access connectors create stock-connector --region us-east1 --range 10.8.0.0/28 --network default`
    3. **FW設定**: `gcloud compute firewall-rules create allow-vpc-connector --allow tcp:5432 --source-ranges 10.8.0.0/28`
    4. **Cloud Run設定**: `gcloud run services update stock-web-ui --vpc-connector stock-connector --region us-east1`
    5. **DB接続**: 環境変数 `DB_HOST` に GCEのプライベートIPを設定
* [x] **Secret Manager の適用 (Phase 5残件)**
  * 本番運用において `KEY.json` を含めるのはリスクがあるため、Secret Manager 経由での取得に切り替える。

---

## フェーズ7：本番OSS運用開始

* [ ] WebUI 公開（制限付き）
  * [x] ロールバックの追加
  * [ ] UI改善点の洗い出し
    * [x] 各ステータス，目的でソート，フィルタリング
    * [ ] 全体的な成績を表示する
  * [ ] 必要な項目の追加
    * [x] 株や資産の購入，売却
    * [ ] CheckSignalボタンの内容確認,修正
    * [ ] Updateでmy_stockと表示銘柄の不一致を解消
  * [ ] **UIの「README化」改修 (Self-Documenting UI)**
    * [ ] **コンセプト/ポリシーの明示**: ヘッダー直下に概要と運用ポリシー（Active Rules等）を表示
    * [ ] **言語と用語の統一**: 日英混在を解消し、原則日本語（または意図的な併記）に統一
    * [ ] **操作の透明性向上**: Update/Check/Simulationボタンに「何が起きるか（副作用）」の補足説明を追加
    * [ ] **ダッシュボードの自己説明化**: Empty State時の誘導、各指標（MACD等）へのツールチップ解説追加
    * [ ] **システム状態の可視化**: 最終更新日時、Region、Version等のメタ情報をフッター表示
* [ ] **セキュリティ・コンプライアンス対応 (必須)**
  * [ ] **今後も保守開発をするためにgit追跡自体は続ける**
  * [ ] **Git履歴の浄化**: 過去のコミットに含まれる `KEY.json` や `.env` などの機密情報を完全に削除 (BFG Repo-Cleaner や `git filter-repo` を使用、あるいは `.git` 再作成)。
  * [x] **ハードコードされたパスの修正**: `/Users/niwa_kazuhiro/...` などの絶対パスを相対パスや環境変数利用に書き換え。
  * [ ] **個人につながる情報の削除**
  * [ ] **シークレットスキャン**: `trufflehog` 等でリポジトリをスキャンし、漏洩がないか確認。
  * [ ] **LICENSEファイルの追加**: MIT License 等、適切なライセンスを配置。
* [ ] **ドキュメント整備**
  * [x] **README.md の刷新**: `Docs/WayToBenefit.md` の指針に従い、「裁量トレード支援ツール」としての思想を強調。セットアップ手順の明確化。
  * [ ] 各ディレクトリにあるREADMEの更新・不要な個人メモの削除。

* [ ] cron 有効化
* [ ] 監視開始

* [ ] **OSSドキュメント拡充**
  * [ ] `CONTRIBUTING.md` 作成（PR/Issueのガイドライン）
  * [ ] `ARCHITECTURE.md` 作成（データフロー詳細）

## フェーズ8：将来拡張検討

Docs/WayToBenefit.md の「ニッチ・実運用」戦略に基づき再評価：

* [ ] **通知システムの優先度向上 (High Priority)**
  * [ ] Slack/Discord/LINE連携を早期に検討 (Why: 監視ツールとしてPush通知は必須機能。能動的な確認を減らすため)
  * [ ] 通知フィルタクラスの実装 (`NotificationManager`)
* [ ] **優待(Present)管理機能 (High Priority)**
  * [ ] 優待内容,必要株数,権利確定月,配当利回りのDB化 (Why: 日本株個人投資家の強力なニーズ)
* [ ] **UI/UXのモダン化**
  * [ ] python/web/templates/index.htmlをモダンなFrameworkに書き換え（React/Vue.jsなど）
* [ ] **外部連携**
  * [ ] 証券会社API入力エリア
* [ ] **(Low Priority) 国際市場・英語対応**
  * [ ] ※ `WayToBenefit.md` の「日本株スイング特化」という強みが薄れるため、優先度は下げる。あくまでオプション扱い。
* [ ] **リファクタリング**
    [ ] 現在fastAPIのみで書かれているがこれをver1としてドキュメント作成し終わったら,フロントはnext,バックはgo，計算はpythonに業務を分割する
