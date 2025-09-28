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
`python main.py daily`
市場開場前（午前9時前）と閉場後（午前9時以降）で異なる処理を実行します。
- **市場開場前**: 前日の日次レポートを生成し、Slackに送信します。
- **市場閉場後**: 日足データの集計、全銘柄の売買タイミング分析（直近1ヶ月）、全銘柄チャートの一括生成（1ヶ月）、当日の日次レポートのSlack送信、全銘柄の急落検知とテクニカル指標に基づく警告を行います。
  - **生成されるファイル**:
    - `data/report/daily/summary/summary_report_YYYYMMDD_HHMMSS.txt` (サマリーレポート)
    - `data/report/daily/detailed/detailed_report_YYYYMMDD_HHMMSS.txt` (詳細レポート)
    - `data/chartImg/1mo/*.png` (全銘柄チャート画像)
    - `data/plots/1mo/*.png` (テクニカル指標プロット画像)

# 週次タスクの実行
`python main.py weekly`
週次タスクを実行します。
- 全銘柄の売買タイミング分析（直近3ヶ月）、全銘柄チャートの一括生成(3ヶ月)、ポートフォリオ分析、週次レポートのSlack送信を行います。
  - **生成されるファイル**:
    - `data/report/weekly/summary/summary_report_YYYYMMDD_HHMMSS.txt` (サマリーレポート)
    - `data/report/weekly/detailed/detailed_report_YYYYMMDD_HHMMSS.txt` (詳細レポート)
    - `data/chartImg/3mo/*.png` (全銘柄チャート画像)
    - `data/plots/3mo/*.png` (テクニカル指標プロット画像)

# 月次タスクの実行
`python main.py monthly`
月次タスクを実行します。
- 四半期データの収集・分析、全銘柄の売買タイミング分析（直近6ヶ月）、全銘柄チャートの一括生成(6ヶ月)、trading ruleの見直し,月次レポートのSlack送信を行います。
  - **生成されるファイル**:
    - `data/report/monthly/detailed/detailed_report_YYYYMMDD_HHMMSS.txt` (詳細レポート)
    - `data/report/monthly/trading_rules/trading_rules_YYYYMMDD_HHMMSS.txt` (トレーディングルール見直しレポート)
    - `data/chartImg/6mo/*.png` (全銘柄チャート画像)
    - `data/plots/6mo/*.png` (テクニカル指標プロット画像)

# 年次タスクの実行
`python main.py yearly`
年次タスクを実行します。
- 全銘柄の売買タイミング分析（直近1年）、`my_stock.db` のアーカイブ（CSV形式でのダンプ）を行います。
  - **生成されるファイル**:
    - `data/archive/my_stock_YYYYMMDD_HHMMSS.csv` (データベースのCSVダンプ)

# リアルタイム監視モード (バックグラウンドで実行)
`python main.py always`
システムをリアルタイム監視モードで起動し、以下のバックグラウンドタスクを常時実行します。
- **watchタスク**: 市場開閉に合わせて株価をリアルタイムで監視し、分足データを取得します。
- **monitorタスク**: システムのリソース使用率（CPU、メモリ、DBサイズ、APIコール数）を定期的にログに記録します。
- **分足監視タスク**: 市場開場中に15分足データを分析し、速報アラートを送信します。
- **日足分析タスク**: 終値確定後に日足データを分析し、急落検知やテクニカル指標に基づく警告を行います。
このモードは、システムを継続的に稼働させる運用環境向けです。
  - **生成されるファイル**:
    - `data/crash_flags/*.flag` (急落検知フラグファイル)
    - `log/*.log` (システムログファイル)
    - (データベースに分足・日足データが保存されますが、ファイルとしては直接生成されません)

# リアルタイム監視モードのテスト実行 (1回のみ実行)
`python main.py always-test`
`always` モードで実行される各バックグラウンドタスク（watch, monitor, analyze）をそれぞれ1回だけ実行し、動作確認を行います。
市場が閉場している場合は、watchタスクとanalyzeタスクはスキップされます。
  - **生成されるファイル**:
    - `data/crash_flags/*.flag` (急落検知フラグファイル - テスト実行時)
    - `log/*.log` (システムログファイル - テスト実行時)
    - (データベースへのデータ保存はテストモードではスキップされる場合があります)
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
