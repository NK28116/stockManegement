# GCPアカウント移行手順書

本ドキュメントは、プロジェクトを管理するGoogleアカウントが変更されたことに伴い、既存のGCP環境から新しいGCP環境（新プロジェクト）へインフラとデータを移行するための手順をまとめたものです。

## 概要
GCPのリソースはアカウント間・プロジェクト間で直接「移動」することができないものが多いため、基本的には**「新環境でのインフラ再構築」と「旧環境からのデータ移行」**という手順になります。

---

## 1. 事前準備（新アカウントでのセットアップ）

1. **新プロジェクトの作成**
   - 新しいGoogleアカウントでGCPコンソールにログインし、新しいプロジェクト（例: `stockmanagement-v2`）を作成します。
   - 請求先アカウント（Billing）を紐付けます。
2. **APIの有効化**
   - 新プロジェクトで以下のAPIを有効化します。
     - Cloud Run API
     - Cloud SQL API
     - Compute Engine API
     - Cloud Storage API
     - Secret Manager API
     - Serverless VPC Access API
     - IAM Service Account Credentials API
3. **ローカル環境の切り替え**
   - `gcloud auth login` で新アカウントにログインします。
   - `gcloud config set project [新プロジェクトID]` を実行します。

---

## 2. データベースとストレージの移行

### 2.1 PostgreSQL (GCE上のDocker) のデータ移行
本プロジェクトは Always Free 枠に完全に収めるため、有償のCloud SQLではなくGCEインスタンス上でPostgreSQLをコンテナ稼働させる設計とします。
1. 旧GCEインスタンスにSSH接続し、`pg_dump` コマンド等を用いてデータベースのバックアップ（ダンプファイル）を作成します。
2. ダンプファイルをGCS経由、またはローカル経由で新環境のGCEインスタンスへ転送します。
3. 新環境のGCE（`e2-micro`）上でPostgreSQLコンテナを起動し、データをリストアします。

### 2.2 Cloud Storage (GCS) の移行
> **注意**: GCSのバケット名は**世界中で一意**である必要があります。旧バケットを削除しない限り同じ名前は使えないため、新しい名前（例: `stock-management-prod-v2`）にするか、旧バケットを削除してから作成する必要があります。
1. 新プロジェクトでGCSバケットを作成します。
2. Storage Transfer Service や `gcloud storage cp` を用いて、旧バケットのデータを新バケットへコピーします。

---

## 3. シークレットと権限 (IAM) の移行

1. **Secret Manager の再登録**
   - 新環境の Secret Manager に、APIキーなどのシークレット値を再登録します。
2. **Workload Identity Federation (WIF) の再設定**
   - GitHub Actions 用の認証設定をやり直します。
   - プロジェクト内の `scripts/setup_wif.sh` を新プロジェクトIDに合わせて修正・実行し、新しいプロバイダID等を取得します。
3. **GitHub Secrets の更新**
   - GitHubリポジトリの `Settings > Secrets and variables > Actions` を開き、以下を新環境の値に更新します。
     - `GCP_PROJECT_ID`
     - `GCP_WIF_PROVIDER`
     - `GCP_SERVICE_ACCOUNT`

---

## 4. ネットワークとインフラの再構築 (Always Free最適化)

1. **GCE (定期実行 兼 DB用VM) の構築**
   - 新環境で Always Free 枠対象となる `e2-micro` インスタンス（リージョン: `us-east1`, `us-central1`, `us-west1` のいずれか、標準永続ディスク30GB以内）を作成します。
   - Python、Docker、ソースコードを配置し、PostgreSQLコンテナを立ち上げます。
   - `makefile` に記載された `make install-cron` を実行して crontab を再設定します。
2. **VPC コネクタの廃止と Direct VPC Egress の採用**
   - 以前は Cloud Run から GCE (DB) に接続するために有償の「VPC アクセスコネクタ」を使用していましたが、これを廃止します。
   - 代わりに、追加コストがかからない **Direct VPC Egress** を用いてCloud RunとGCEを接続します。
3. **ファイアウォールルールの設定**
   - Cloud Run (Direct VPC Egress) からの内部トラフィックが GCE インスタンス (TCP:5432) に到達できるよう、ファイアウォールルールを設定します。

---

## 5. アプリケーションのデプロイとコード修正

1. **環境変数の修正**
   - プロジェクト内の `.env` やハードコードされている可能性のある部分を更新します。
     - `GOOGLE_CLOUD_PROJECT` の値を新プロジェクトIDに変更。
     - `GCS_BUCKET_NAME` などを新バケット名に変更。
     - `DB_HOST` を新GCEインスタンスの内部（プライベート）IPに変更。
2. **Cloud Run のデプロイ (Direct VPC Egress適用)**
   - 新プロジェクトの Artifact Registry (または GCR) に対してイメージをビルド＆プッシュします。
   - Cloud Run サービスを新規デプロイする際、有償のVPCコネクタではなく `--vpc-egress=private-ranges-only` 等を指定して Direct VPC Egress を有効化し、GCEのプライベートIPへ無料で通信できるようにマッピングします。

---

## 6. 旧環境のシャットダウン
- 新環境でUIの表示、バッチ処理、DBへの書き込みがすべて正常に行われていることを確認（並行稼働）した後、旧GCPプロジェクトのリソースを削除（またはプロジェクトごとシャットダウン）します。
