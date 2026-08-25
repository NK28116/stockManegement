# v1.1 — 運用・UX安定化

統合ブランチ: `integration/v1.1-ops-ux-stabilization` (base: `develop`)

## スコープ

| チケット | 内容 | ブランチ |
| --- | --- | --- |
| PRIDEV-481 | 単一パスワード認証の実装 | `feature/add-password-auth-PRIDEV-481` |
| PRIDEV-482 | matplotlib 日本語表示の修正と回帰テスト | `fix/matplotlib-japanese-font-PRIDEV-482` |
| PRIDEV-484 | ドロップダウン配置と小画面 overflow の修正 | `fix/dropdown-layout-overflow-PRIDEV-484` |
| PRIDEV-485 | 初回起動待ち時間の短縮と失敗時 UX 改善 | `fix/startup-wait-ux-PRIDEV-485` |
| PRIDEV-486 | プルダウン選択肢の補完と UI 回帰テスト | `fix/dropdown-options-PRIDEV-486` |
| PRIDEV-487 | Alembic 整合・検証コマンド・回帰テスト | `fix/alembic-schema-consistency-PRIDEV-487` |
| PRIDEV-490 | Cloud Logging / Monitoring 読み取りアダプタ | `feature/add-cloud-observability-adapter-PRIDEV-490` |
| PRIDEV-491 | 異常検知・System Health 集約サービス | `feature/add-system-health-service-PRIDEV-491` |
| PRIDEV-492 | 管理者専用 System Monitor API | `feature/add-system-monitor-api-PRIDEV-492` |
| PRIDEV-493 | System Monitor 画面 | `feature/add-system-monitor-ui-PRIDEV-493` |
| PRIDEV-494 | System Monitor 認証・異常系 E2E テスト | `feature/add-system-monitor-e2e-PRIDEV-494` |

エピック PRIDEV-483 / 488 / 489 は上記子チケットの束ねであり、単独の実装はない。

## マージ順序

依存関係があるため、次の順にマージする。

```
PRIDEV-481 ─┐
PRIDEV-490 ─┴→ PRIDEV-491 → PRIDEV-492 → PRIDEV-493 → PRIDEV-494
PRIDEV-482 / 484 / 485 / 486 / 487 (独立)
```

`PRIDEV-485` と `PRIDEV-481` はどちらも `python/web/app.py` を変更するため、
後からマージする側で軽微な競合解消が必要になる。

## デプロイ前に必要な設定

| 環境変数 | チケット | 必須 | 備考 |
| --- | --- | --- | --- |
| `APP_PASSWORD_HASH` | 481 | ○ | 未設定だと**認証が無効になる**。生成は `python scripts/hash_password.py` |
| `AUTH_SECRET_KEY` | 481 | ○ | 未設定だと再起動でログアウトされる |
| `GCP_PROJECT_ID` | 490 | ○ | 未設定だと System Monitor は degraded 表示になる |

必要な IAM ロール: `roles/logging.viewer` / `roles/monitoring.viewer` (書き込み権限は不要)。

DB は適用後に `make db-check` で整合を確認する。

## ユーザー確認待ちの値

以下は暫定値で実装済み。確定後は各設定値 1 箇所の変更で反映される。

| チケット | 項目 | 暫定値 | 設定先 |
| --- | --- | --- | --- |
| 481 | セッション有効期限 / 失敗許容回数 / ロック時間 | 12 時間 / 5 回 / 15 分 | `python/web/auth.py` |
| 485 | 起動目標 / loading 表示遅延 / timeout | 10 秒 / 1 秒 / 30 秒 | `python/web/startup.py` |
| 486 | プルダウンの選択肢 | **未変更** (差分を記録のみ) | `python/web/constants.py` |
| 490 | 取得期間 / 件数 / 監視指標 | 24h / 7日 / 100件 / 500件 / 6指標 | `python/observability/settings.py` |
| 493 | 初期表示 / 追加読み込み / 最大表示 | 20 件 / あり 20 件 / 100 件 | `python/web/routes/system_monitor.py` |

## 関連ドキュメント

- `Docs/AUTH_SETUP.md` — パスワード認証の設定
- `Docs/CHART_FONT_SETUP.md` — チャートの日本語フォント
- `Docs/DB_MIGRATION.md` — DB マイグレーション運用
- `Docs/OBSERVABILITY.md` — Cloud Logging / Monitoring と System Health
- `Docs/SYSTEM_MONITOR_E2E.md` — System Monitor の E2E テスト
