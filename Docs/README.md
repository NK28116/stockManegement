# ドキュメント一覧

## まず読むもの

| 文書 | 内容 |
| --- | --- |
| [HOW_IT_WORKS.html](HOW_IT_WORKS.html) | アプリのしくみ (使っている数学と Web の技術) を高校生向けに解説。ブラウザで直接開けます |
| [architecture.md](architecture.md) / [design.md](design.md) | 全体構成と設計 |

## セットアップと運用

| 文書 | 内容 |
| --- | --- |
| [AUTH_SETUP.md](AUTH_SETUP.md) | パスワード認証の設定 |
| [SECRETS_BITWARDEN.md](SECRETS_BITWARDEN.md) | 秘密情報を Bitwarden で管理し、`make env` で `.env` を生成する |
| [CHART_FONT_SETUP.md](CHART_FONT_SETUP.md) | チャートの日本語フォント |
| [STOCK_STATUS.md](STOCK_STATUS.md) | 銘柄ステータスの定義とデータ移行 |
| [DB_MIGRATION.md](DB_MIGRATION.md) | DB マイグレーションの運用 |
| [OBSERVABILITY.md](OBSERVABILITY.md) | Cloud Logging / Monitoring と System Health |
| [SYSTEM_MONITOR_E2E.md](SYSTEM_MONITOR_E2E.md) | System Monitor の E2E テスト |
| [RELEASE_v1.1.md](RELEASE_v1.1.md) | v1.1 のリリースノートとデプロイ前の作業 |
| [DEPLOY_v1.1.md](DEPLOY_v1.1.md) | v1.1 を本番に出す手順 (チェックリスト・切り戻し) |
| [GCP_Migration_Guide.md](GCP_Migration_Guide.md) / [HowTopostgreSQLByORM.md](HowTopostgreSQLByORM.md) | GCP 移行と PostgreSQL 操作の手順 |

セキュリティ上の注意は [`../SECURITY.md`](../SECURITY.md)、第三者ライセンスは [`../THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) を参照してください。

## 開発の記録

以下は開発当時のメモ・計画・レビューです。現在のコードと一致しない記述が含まれることがあります。
インフラの識別子 (プロジェクト ID、URL など) は `<GCP_PROJECT_ID>` のようなプレースホルダーに置き換えています。

| 文書 | 内容 |
| --- | --- |
| [GoalToDeploy.md](GoalToDeploy.md) | デプロイまでの計画とチェックリスト |
| [change-log.md](change-log.md) | 変更ログ |
| [requirements.md](requirements.md) / [review.md](review.md) | 週足スイング分析の要件と実装レビュー |
| [CreateWebUI.md](CreateWebUI.md) / [CreateWatchTask_Phase4.md](CreateWatchTask_Phase4.md) / [TradingRulesUIStatus.md](TradingRulesUIStatus.md) | 機能ごとの実装メモ |
| [ToDoFromIssue.md](ToDoFromIssue.md) | 課題から整理した作業リスト (2026-06 時点) |
| [WayToBenefit.md](WayToBenefit.md) / [idea.md](idea.md) | 提供価値・今後のアイデア |
| [daily_notes/](daily_notes/) | 開発日次ノート |
| [ai-rules.md](ai-rules.md) / [workflow.md](workflow.md) / [ci-cd.md](ci-cd.md) / [coding-standards.md](coding-standards.md) / [release-strategy.md](release-strategy.md) / [decisions.md](decisions.md) | 開発の進め方 |
