# Security Policy

## 脆弱性の報告

セキュリティ上の問題を見つけた場合は、**公開の Issue には書かず**、GitHub の
[Private vulnerability reporting](https://github.com/NK28116/stockManegement/security/advisories/new)
から報告してください。再現手順と影響範囲を書いていただけると助かります。
この窓口が使えない場合は、詳細を書かずに「セキュリティについて連絡したい」とだけ Issue に書いてください。連絡方法をこちらからお知らせします。

対象は `develop` ブランチの最新版です。

## 秘密情報の扱い

このリポジトリは公開されています。次のものは**コミットしないでください**。

| 種類 | 例 | 置き場所 |
| --- | --- | --- |
| 認証情報 | `.env`、サービスアカウント鍵 (`*.json`)、API トークン、Webhook URL | ローカルの `.env` / 本番は Secret Manager や PaaS の環境変数 |
| パスワード | 平文のパスワード | パスワードマネージャーのみ。アプリには `APP_PASSWORD_HASH` (ハッシュ) だけを渡す |
| 個人の取引データ | 実際の保有銘柄・数量・取得単価を含む CSV、DB ダンプ | ローカルまたは非公開の GCS バケット |
| インフラの識別子 | 外部 IP、本番 URL、プロジェクト番号 | 環境変数。文書では `<GCP_PROJECT_ID>` のようなプレースホルダーを使う |

`.gitignore` と `.dockerignore` で代表的なファイルを除外し、CI (`.github/workflows/secret-scan.yml`) で
gitleaks によるシークレット検出を行っています。

万一コミットしてしまった場合は、履歴から消すだけでは不十分です。**先に鍵・トークンを無効化して再発行**し、
そのあとで履歴の浄化 (`scripts/purge_history.sh`) を検討してください。

## アプリ側の主な対策

- 管理画面・API は単一パスワード認証で保護し、公開パスは明示したものだけにしています (`Docs/AUTH_SETUP.md`)
- パスワードは PBKDF2-SHA256 でハッシュ化して保持し、セッション Cookie は HMAC で署名しています
- 本番環境で認証設定が不足している場合は起動しません (フェイルクローズ)
- System Monitor が表示するログは、トークン・パスワード・API キーなどをマスクしてから返します (`Docs/OBSERVABILITY.md`)
