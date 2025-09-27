# Stock Management System

このプロジェクトは、株価データの収集、分析、監視、およびポートフォリオ管理を自動化するためのシステムです。Pythonで実装されており、日次、週次、月次、年次の各タスクを自動実行し、市場の動向に基づいた洞察を提供します。

## 主な機能

- **株価データ収集**: `yfinance`などのライブラリを使用して、最新の株価データを収集します。
- **テクニカル分析**: 移動平均線、RSI、MACDなどのテクニカル指標を用いて株価を分析し、売買タイミングを特定します。
- **急落検知とアラート**: 市場開場中にリアルタイムで株価を監視し、急落を検知した際にアラートを送信します。
- **ポートフォリオ分析**: 保有銘柄のパフォーマンスを分析し、最適化のためのレポートを生成します。
- **チャート生成**: 分析結果を視覚的に理解しやすいように、様々な種類の株価チャートを自動生成します。
- **レポート機能**: 日次、週次、月次で分析結果や市場の状況をまとめたレポートを生成し、Slackなどのチャネルに通知します。
- **自動タスク実行**: `cron`ジョブと連携し、日次、週次、月次、年次の各タスクを自動で実行します。

## プロジェクト構造

```
.
├── main.py                     # メインスクリプト (タスク実行エントリポイント)
├── requirements.txt            # 依存関係ライブラリ
├── makefile                    # ビルド・実行コマンド定義
├── python/
│   ├── analysis/               # データ分析関連
│   │   ├── data_collector.py   # データ収集
│   │   ├── portfolio_analyzer.py # ポートフォリオ分析
│   │   └── ...
│   ├── db/                     # データベース関連
│   │   ├── database.py         # DB接続・操作
│   │   └── ...
│   ├── trading/                # 売買ロジック関連
│   │   ├── every_stock_buy_and_sell_timing.py # 売買タイミング分析
│   │   └── ...
│   ├── utils/                  # ユーティリティ関数
│   │   ├── alert.py            # アラート通知
│   │   ├── logger.py           # ロギング
│   │   ├── monitor.py          # システム監視
│   │   ├── report.py           # レポート生成・送信
│   │   └── ...
│   ├── visualization/          # データ可視化関連
│   │   ├── generate_all_charts.py # チャート一括生成
│   │   └── ...
│   └── watch/                  # リアルタイム監視関連
│       ├── analyze.py          # 分足・日足分析
│       ├── dailyAggregator.py  # 日次データ集計
│       └── watch.py            # 株価リアルタイム監視
├── data/                       # データ保存ディレクトリ
│   ├── db/                     # データベースファイル
│   ├── chartImg/               # 生成されたチャート画像
│   └── ...
└── tests/                      # テストコード
```

## セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env` ファイルを作成し、必要なAPIキーや設定を記述します。
例:
```
SLACK_WEBHOOK_URL=YOUR_SLACK_WEBHOOK_URL
API_KEY=YOUR_API_KEY
```

### 3. データベースの初期化

```bash
make init-db
```

## 使い方

`main.py` を直接実行するか、`makefile` を使用してタスクを実行します。

### 手動実行

```bash
# 日次タスクの実行
python main.py daily

# 週次タスクの実行
python main.py weekly

# 月次タスクの実行
python main.py monthly

# 年次タスクの実行
python main.py yearly

# リアルタイム監視モード (バックグラウンドで実行)
python main.py always

# リアルタイム監視モードのテスト実行 (1回のみ実行)
python main.py always-test
```

### Makefile を使用した実行

`makefile` には、開発や運用に便利なコマンドが定義されています。

```bash
# 全ての依存関係をインストール
make install

# データベースを初期化
make init-db

# リアルタイム監視を開始
make watch-realtime

# 全銘柄の分析を実行
make analyze

# 特定の銘柄を分析 (例: コード1234)
make analyze-stock CODE=1234

# 日次タスクを実行
make run-daily

# 週次タスクを実行
make run-weekly

# 月次タスクを実行
make run-monthly

# cronジョブをインストール
make install-cron

# ヘルプを表示
make help
```

## 開発

### テストの実行

```bash
make test
```

### コードのフォーマットとリンティング

```bash
make format
make lint
```

## 貢献

このプロジェクトへの貢献を歓迎します。バグ報告、機能提案、プルリクエストなど、お気軽にお寄せください。

## ライセンス

このプロジェクトは [MIT License](LICENSE) の下でライセンスされています。
