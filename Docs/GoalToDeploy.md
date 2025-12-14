# フェーズ0：前提整理（必須）

### 0-1. デプロイ形態の最終決定

* [ ] **WebUI：Cloud Run**
* [ ] **定期実行：GCE（既存）**
* [ ] **永続ストレージ：GCS**

※ ここでは「GCEは既にある前提」で進めます。

---

# フェーズ1：ルール管理の確定（最重要）

### 1-1. trading_rules.json の正式スキーマ確定

* [ ] version フィールド追加
* [ ] 有効/無効フラグ
* [ ] 数値の単位・許容範囲定義
* [ ] UI ↔ JSON ↔ Python の完全一致

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

* [ ] `TradingRules` schema が上記構造を読む
* [ ] `ImprovedTradingRules.__init__` が JSON を直接受け取れる
* [ ] config.py フォールバック確認

---

### 1-3. ルール履歴管理

* [ ] `trading_rules/active.json`
* [ ] `trading_rules/history/YYYYMMDD_HHMMSS.json`
* [ ] WebUI保存時に **必ず履歴保存**

---

# フェーズ2：GCS 設計・実装

### 2-1. GCS バケット作成

* [ ] `stock-management-prod`（1バケットで十分）

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

---

### 2-3. ローカル → GCS 移行

* [ ] chartImg → `charts/`
* [ ] report → `reports/`
* [ ] data 保存先を **GCSに切替**

---

# フェーズ3：WebUI（Cloud Run）デプロイ準備

### 3-1. app.py の責務分離

* [ ] WebUI は「読む・書く」だけ
* [ ] 分析ロジックを一切持たない

---

### 3-2. GCS I/O 実装

* [ ] rules の GET/POST が GCS 直結
* [ ] charts は署名URL or public read

---

### 3-3. Dockerfile 作成

* [ ] Python slim
* [ ] requirements.txt
* [ ] gunicorn 起動

---

### 3-4. Cloud Run 設定

* [ ] 認証：IAP or 簡易 Basic Auth
* [ ] メモリ 512MB
* [ ] 常時起動不要（0スケール可）

---

# フェーズ4：定期実行（自動監視）

### 4-1. 実行方式決定

**どちらか一択**

* [ ] GCE cron（既存）

---

### 4-2. 実行時フロー整理

* [ ] GCS から `active.json` 読む
* [ ] 指標計算
* [ ] charts 出力 → GCS
* [ ] シグナル判定
* [ ] Slack 通知

---

### 4-3. 冪等性確認

* [ ] 同日複数回実行OK
* [ ] 上書き or 日時別保存

---

# フェーズ5：セキュリティ・運用最低限

### 5-1. 認証情報整理

* [ ] APIキーは Secret Manager
* [ ] KEY.json 排除

---

### 5-2. IAM

* [ ] Cloud Run → GCS read/write
* [ ] cron 実行用 SA 限定権限

---

### 5-3. ログ

* [ ] Cloud Logging 有効
* [ ] 異常検知ログ

---

# フェーズ6：本番前チェック（必須）

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

# フェーズ7：本番運用開始

* [ ] WebUI 公開（制限付き）
* [ ] cron 有効化
* [ ] 監視開始

# フェーズ8：将来拡張検討

Docs/WayToBenefit.mdを参考に、以下の拡張を検討

* [ ] 高度ルール追加
* [ ] Privateな情報を削除
* [ ] READMEを含めたDocsの編集などのOSS公開準備
* [ ] 監視市場の追加 <- 収益化可能性
* [ ] 英語圏に対応 <- 収益化可能性
* [ ] 通知ツールの追加（LINE, Discordなど）
