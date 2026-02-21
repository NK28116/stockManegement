# Linear Task Import List

このドキュメントは `Docs/GoalToDeploy.md` の未完了タスクを Linear MCP で登録しやすい形式にまとめたものです。
Claude Code で読み込み、Linear の `CreateIssue` ツール等を用いて登録してください。

---

## 🏗 Architecture & Refactoring

### Title: [Refactor] app.py の責務分離とロジック排除
- **Priority**: High
- **Description**:
  WebUI (`app.py`) が分析ロジックを持たず、データの読み書き（Viewer/Editor）に徹するようにリファクタリングする。
  - **現状**: `app.py` 内に一部の計算やロジックが含まれている可能性がある。
  - **Goal**: WebUI は GCS/DB からの結果表示と、設定ファイル (`json`) の更新のみを担当する。
  - **DoD**: `app.py` から分析ロジックが排除され、純粋なAPI/UI層として動作する。

---

## 🔒 Security & Infrastructure

### Title: [Infra] IAM権限の最小化と整理
- **Priority**: High
- **Description**:
  各コンポーネントのIAM権限を最小権限の原則に従って設定する。
  - **Cloud Run**: GCS への read/write 権限のみを付与（必要であればDB接続権限も）。
  - **Cron (GCE)**: 実行用 Service Account に限定的な権限を付与。
  - **DoD**: 不要な広範囲権限を持ったキーやロールが削除され、Terraform または gcloud コマンドで再現可能になっている。

### Title: [Ops] Cloud Logging の有効化と異常検知
- **Priority**: Medium
- **Description**:
  本番運用に向けてログ監視体制を整える。
  - Cloud Logging エージェントの確認（GCE）と Cloud Run のログ出力確認。
  - **異常検知**: エラーログ（Traceback等）が発生した際に検知できる仕組み（ログメトリクス等）の検討・設定。

### Title: [Security] Git履歴の浄化 (BFG/filter-repo)
- **Priority**: High
- **Description**:
  OSS化および公開に向けて、過去のコミット履歴から機密情報（APIキー、`.env`、個人情報）を完全に削除する。
  - `git filter-repo` または `BFG Repo-Cleaner` を使用。
  - 過去の `KEY.json` やハードコードされたパスが含まれるコミットを抹消する。
  - **DoD**: リポジトリをクリーンな状態で再構築し、`trufflehog` 等のスキャンで警告が出ないこと。

### Title: [Security] シークレットスキャンとLICENSE追加
- **Priority**: High
- **Description**:
  - `trufflehog` 等を使用してリポジトリ内の残留シークレットを検査。
  - 適切な OSS ライセンス（MIT License等）ファイルを作成・配置する。

---

## 💻 WebUI Improvements

### Title: [UI] 全体成績（Performance Summary）の表示
- **Priority**: Medium
- **Description**:
  WebUI 上で現在のポートフォリオまたはバックテストの全体成績を一目で確認できるようにする。
  - 損益推移、勝率、Profit Factor などの主要指標を表示。

### Title: [UI] CheckSignal / Update 機能の不整合解消とUX改善
- **Priority**: Medium
- **Description**:
  - **CheckSignal**: ボタン押下時の処理内容を確認し、意図通り動くよう修正。
  - **Update**: `my_stock.csv` と表示銘柄の不一致が発生しないよう、同期処理を見直す。
  - ユーザーがボタンを押した際に「何が起きるか」がわかるようなフィードバック（Loading表示、完了メッセージ）を追加。

### Title: [UI] Self-Documenting UI への改修
- **Priority**: Medium
- **Description**:
  READMEを読まなくても使い方がわかるUIを目指す。
  - **コンセプト表示**: ヘッダー下に「裁量トレード支援ツール」である旨や運用ポリシーを表示。
  - **用語統一**: 英語/日本語の混在を整理。
  - **ダッシュボード誘導**: データがない場合（Empty State）のガイド表示。
  - **メタ情報**: フッターにバージョン、最終更新日時、Regionなどを表示。

### Title: [UI] UI/UXのモダン化 (将来検討)
- **Priority**: Low
- **Description**:
  現在のテンプレートエンジンベースのUIから、React/Vue.js 等のモダンなフレームワークへの移行を検討・実施する。
  - ※現時点では優先度低。Phase 8。

---

## 📝 Documentation

### Title: [Docs] 各ディレクトリREADMEの整備
- **Priority**: Low
- **Description**:
  プロジェクト内の各ディレクトリにある `README.md` を更新し、最新の構成と役割を反映させる。
  - 不要な個人メモや古い記述を削除する。

### Title: [Docs] OSS用ドキュメントの拡充
- **Priority**: Medium
- **Description**:
  OSSとして公開するための標準ドキュメントを作成する。
  - `CONTRIBUTING.md`: PR/Issue のガイドライン。
  - `ARCHITECTURE.md`: データフロー詳細、システム構成図。

---

## 🚀 Operation & Features (Phase 8)

### Title: [Ops] 定期実行(Cron)の有効化と監視開始
- **Priority**: High
- **Description**:
  GCE 上での cron 実行を正式に有効化し、運用を開始する。
  - ログ監視と合わせて、止まっていないか確認できる状態にする。

### Title: [Feature] 通知システムの強化 (Slack/Discord)
- **Priority**: High
- **Description**:
  シグナル発生時やエラー時にプッシュ通知を送る仕組みを実装する。
  - `NotificationManager` クラスの実装。
  - フィルタリング機能（重要な通知のみ送るなど）。

### Title: [Feature] 株主優待(Present)管理機能の実装
- **Priority**: Medium
- **Description**:
  日本株投資家向け機能として、優待情報の管理機能を追加する。
  - 優待内容、必要株数、権利確定月、配当利回りのDB化と表示。
