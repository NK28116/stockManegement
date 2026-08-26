# Cloud Logging / Monitoring 読み取り (PRIDEV-490)

System Monitor (PRIDEV-491〜493) が参照する読み取り専用アダプタの設定。

## 必要な IAM ロール

アプリのサービスアカウントへ **読み取り権限のみ**を付与する。書き込み権限は不要。

| ロール | 用途 |
| --- | --- |
| `roles/logging.viewer` | Cloud Logging の読み取り |
| `roles/monitoring.viewer` | Cloud Monitoring の読み取り |

## 環境変数

| 環境変数 | 既定値 | 説明 |
| --- | --- | --- |
| `GCP_PROJECT_ID` | (なし) | 対象プロジェクト。`GOOGLE_CLOUD_PROJECT` / `PROJECT_ID` も参照される。未設定なら「取得不能」として扱われる |
| `OBSERVABILITY_LOG_DEFAULT_LOOKBACK_HOURS` | `24` | ログのデフォルト取得期間 |
| `OBSERVABILITY_LOG_MAX_LOOKBACK_DAYS` | `7` | ログの最大取得期間 |
| `OBSERVABILITY_LOG_DEFAULT_LIMIT` | `100` | ログのデフォルト取得件数 |
| `OBSERVABILITY_LOG_MAX_LIMIT` | `500` | ログの最大取得件数 |
| `OBSERVABILITY_MONITORED_METRICS` | 候補すべて | 監視対象指標 (カンマ区切り)。候補外の指定は無視される |

既定値はユーザー確認済みの確定値。変更する場合は
`python/observability/settings.py` の既定値定数、または上記環境変数の
どちらか 1 箇所を変更すれば全体へ反映される。

## 監視指標 (ユーザー確認済み)

| 指標名 | 内容 |
| --- | --- |
| `service_up` | サービス / プロセスの稼働状態 |
| `cpu_utilization` | CPU 使用率 |
| `memory_utilization` | メモリ使用率 |
| `error_count` | 5xx またはエラー数 |
| `response_latency` | レスポンスタイム |
| `last_success_at` | 最終正常実行時刻 (Monitoring ではなく Logging 側から算出) |

GCE / Cloud Run で Cloud Monitoring の metric type が異なるため、
`K_SERVICE` の有無で実行環境を判定して吸収している。

## 上限の適用

`fetch_recent(lookback_hours=..., limit=...)` に上限を超える値を渡しても、
必ず設定値まで丸められる。SDK が上限より多く返した場合も件数で打ち切る。

## エラーの扱い

GCP SDK の例外は上位層へそのまま伝播せず、次のいずれかへ正規化される。
元例外は `__cause__` に保持されるが、メッセージにはリソース名等を含めない。

| 内部エラー | 条件 |
| --- | --- |
| `ObservabilityPermissionError` | 権限不足 (`PermissionDenied` / 401 / 403 等) |
| `ObservabilityUnavailableError` | 到達不能・設定不足・依存未導入・その他 |

Monitoring の個別指標が取れない場合は例外ではなく
`MetricSample.unavailable(...)` (`available=False`, `value=None`) として返す。

## テスト

```bash
PYTHONPATH=. pytest tests/test_observability_adapters.py -v
```

GCP API は呼ばず、注入したモッククライアントで検証する。

## System Health 集約 (PRIDEV-491)

`python/observability/health.py` の `SystemHealthService` が、Logging / Monitoring
の結果を上位層向けの単一モデル `SystemHealth` へ集約する。

```python
from python.observability import SystemHealthService

health = SystemHealthService().collect()
health.to_dict()   # System Monitor API / 画面はこれだけを参照する
```

### 状態

| status | 条件 |
| --- | --- |
| `ok` | エラー・警告なし |
| `warning` | WARNING のログがある |
| `error` | ERROR 以上のログがある |
| `degraded` | Cloud Logging / Monitoring を取得できなかった |

`collect()` は **例外を投げない**。Cloud API の失敗は `degraded_reasons` へ
理由を積み、`status=degraded` として返す。

### 秘匿処理

`recent_errors` のメッセージとラベルは必ず `python/observability/masking.py` を
通る。マスク対象は次のとおり。

- URL のクエリ文字列 (丸ごと `***`)
- `Authorization` / `Cookie` / `Set-Cookie` / `Proxy-Authorization` ヘッダ
- キー名に `token` / `password` / `secret` / `api_key` / `credential` / `session` /
  `signature` / `private_key` / `auth` を含む `key=value`・`key: value`・JSON

判定は値の形ではなくキー名で行うため、未知の値でも取りこぼさない。

```bash
PYTHONPATH=. pytest tests/test_system_health.py -v
```
