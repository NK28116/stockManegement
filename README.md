# Stock Management System (裁量トレード支援ツール)

## 概要

本システムは、日本株のスイングトレードを対象とした**裁量トレード支援システム**です。
「自動で売買を行って利益を出すBot」ではなく、トレーダーが自身のルールに基づき、適切なタイミングで判断を下すための「監視・分析・記録」を自動化することを目的としています。

## コンセプト

* **自動売買ではなく「支援」**: 最終的な売買判断は人間が行います。システムは判断に必要な情報を整理し、ルール逸脱を監視します。
* **実運用前提の設計**: 勉強用のサンプルコードではなく、実際にcronでの常時監視、ルールの外部化、ログ記録を行うことを前提に設計されています。
* **スイングトレード特化**: デイトレードのような高頻度取引ではなく、中期的なトレンドフォローを想定しています。

## 主な機能

1. **市場監視 & 分析**
    * 定期的な株価データの取得とテクニカル指標（MACD, Bollinger Bands等）の計算。
    * 設定されたトレードルールに基づくシグナル検知。

2. **Web UI (Dashboard & Settings)**
    * **Dashboard**: 分析結果やチャート画像をブラウザ上で閲覧可能。
    * **Settings**: プログラムを停止することなく、JSONベースでトレードルール（損切りライン、利確ラインなど）を調整可能。

3. **ルール管理 & 記録**
    * トレードルールの変更履歴を保存し、「なぜルールを変えたか」を記録・追跡可能。
    * 定量的な基準（Profit Factor, Drawdown等）に基づくルール見直しアラート。

## アーキテクチャ

```mermaid
graph TD
    User[User] -->|Browser| WebUI[Web UI (Cloud Run)]
    WebUI -->|Read/Write| Rules[Rules JSON (GCS)]
    WebUI -->|Read| Charts[Charts (GCS)]
    
    Cron[Cron Job (GCE)] -->|Read| Rules
    Cron -->|Fetch| MarketData[Market Data]
    Cron -->|Analyze| Logic[Analysis Logic]
    Logic -->|Save| DB[(PostgreSQL)]
    Logic -->|Generate| Charts
```

* **Backend**: Python, FastAPI
* **Frontend**: HTML, Vue.js (Web UI)
* **Database**: PostgreSQL (SQLAlchemy + Alembic)
* **Infrastructure**: Google Cloud Platform (Cloud Run, GCE, GCS)

## セットアップ手順 (開発環境)

### 前提条件

* Python 3.12+
* Docker & Docker Compose (DB用)

### インストール

1. リポジトリのクローン

    ```bash
    git clone https://github.com/your-account/stockManagement.git
    cd stockManagement
    ```

2. 依存ライブラリのインストール

    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

3. データベースの起動

    ```bash
    docker-compose up -d db
    ```

4. Web UIの起動

    ```bash
    uvicorn python.web.app:app --reload --port 8888
    ```

    ブラウザで `http://localhost:8888` にアクセスしてください。

## 免責事項

本ソフトウェアは、株式取引の分析支援を目的としていますが、利益を保証するものではありません。
本ソフトウェアの利用によって生じた、いかなる損害についても開発者は責任を負いません。投資判断は自己責任で行ってください。

## License

MIT License
