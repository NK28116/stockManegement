# 株式投資分析・運用システム

## 概要

このシステムは、保有株式のポートフォリオ分析、売買タイミングの判定、リスク管理を支援するPythonベースのツールです。個人の投資家が市場の変動に対応し、より情報に基づいた意思決定を行うことを目的としています。

## 特徴

- **ポートフォリオ分析**: 保有株式全体のパフォーマンスを詳細に分析します。
- **売買タイミング分析**: テクニカル指標に基づき、買い・売りシグナルを生成します。
- **リアルタイム監視**: 市場の急変（暴落など）を検知し、アラートを発します。
- **カスタマイズ可能なリスク管理**: ストップロスや利確の閾値を柔軟に設定できます。
- **豊富な可視化機能**: チャートやグラフで市場の動向や分析結果を直感的に把握できます。

## セットアップ

### 1. 環境準備

プロジェクトを実行するために必要な環境をセットアップします。

```bash
# プロジェクトディレクトリに移動
cd /Users/niwa_kazuhiro/Documents/PrivateDevelop/stockManegement

# 仮想環境の有効化（推奨）
source venv/bin/activate

# 必要なパッケージのインストール
pip install -r requirements.txt
```

### 2. プロジェクト構造

主要なディレクトリとファイルの構成は以下の通りです。

```bash
stockManegement/
├── data/                          # データ保存用
│   ├── my_stock.csv                 # 保有銘柄リスト
│   ├── quarterly_analysis.csv    # 保有銘柄リスト
│   ├── report                    # ポートフォリオテンプレート
│   ｜     ├── summary/           # 分析レポート
│   ｜     ├── detail/            # 分析レポート
│   └── chartImg/                 # チャート画像
｜
├── python/                           # Pythonスクリプト
│   ├── config.py                    # 設定ファイル
｜
│   ├── analysis                     #  分析
│   │   ├── data_collector          # データ収集
│   │   ├── portfolio_analyzer.py   # ポートフォリオ分析
｜
│   ├── trading                      # 売買
│   │   ├── trading_rules.py        # 売買ルール定義
│   │   ├── every_stock_BuySell_timing.py      # 売買タイミング分析
│   │   ├── buy_and_sell_stock.py      # code.csvで銘柄管理
｜
│   ├── watch                          # 暴落に備えた監視
│   │   ├── watch.py                # リアルタイム監視
│   │   ├── analyze.py              # 監視結果分析
│   │   ├── dailyAggregator.py      # 日次集計
｜
│   ├── visualization                 # 可視化ツール
│   │   ├── stock_chart_visualizer.py # チャート作成
│   │   ├── view_charts.py            # チャート確認
│   │   ├── generate_all_charts.py    # 全チャート一括作成
｜
│   ├── utils/                    # ユーティリティ
│   │   ├── alert.py               # アラート機能
│   │   ├── indicator.py           # テクニカル指標計算
｜
│   ├── db                        # データベース
│   │   ├── stock.db           # SQLiteデータベース
  │   └── init_database.py                  # データベース初期化
｜
├── makefile   
└── logs/                         # ログファイル
```

## 使い方

### 1. 保有株式の分析

保有株式の売買タイミングやパフォーマンスを分析します。

```bash
cd python

# 保有株式の売買タイミングを分析
python3 trading/every_stock_BuySell_timing.py ../data/my_stock.csv

# 分析期間を指定（例：6ヶ月）
python3 trading/every_stock_BuySell_timing.py ../data/my_stock.csv --period 6mo
```

### 2. チャートの作成・確認

保有株式のテクニカル指標チャートを作成し、確認します。

```bash
# 保有株式のチャートを作成
python3 visualization/stock_chart_visualizer.py

# 作成されたチャートを確認
python3 visualization/view_charts.py
```

### 3. ポートフォリオ分析

ポートフォリオ全体の健全性を評価し、売買ルールを検証します。

```bash
# ポートフォリオ全体の分析
python3 analysis/portfolio_analyzer.py

# 売買ルールの検証
python3 trading/trading_rules.py
```

### 4. リアルタイム監視

市場の急変に備え、日次で株式を監視します。

```bash
# 日次監視（推奨）
python3 watch/watch.py
```

## 売買タイミングの理解

システムが生成する買い・売りシグナルの主な条件です。

### 買いシグナル

- **++パターン**: 連続上昇（ゴールデンクロス）
- **RSI過売り**: RSI 30以下からの反転
- **価格安値圏**: 長期移動平均線の90%以下

### 売りシグナル

- **--パターン**: 連続下降（デッドクロス）
- **RSI過買い**: RSI 70以上からの反転
- **利確**: 10%利益達成での自動売却
- **ストップロス**: 5%損失での自動売却

## 分析結果の読み方

### 重要な指標

| 指標 | 良い値 | 悪い値 | 説明 |
|------|--------|--------|------|
| **総リターン** | +5%以上 | -5%以下 | 期間中の収益率 |
| **年率リターン** | +10%以上 | -10%以下 | 年間換算の収益率 |
| **ボラティリティ** | 20%以下 | 40%以上 | 価格変動の激しさ |
| **シャープレシオ** | 1.0以上 | 0.5以下 | リスク調整後リターン |
| **最大ドローダウン** | -10%以内 | -20%以下 | 最大の損失幅 |
| **勝率** | 60%以上 | 40%以下 | 利益が出る取引の割合 |

### 分散効果の評価

- 平均相関係数:
  - 0.3未満 → ✅ 良好な分散効果
  - 0.3-0.6 → ⚠️ 中程度の分散効果
  - 0.6以上 → ❌ 分散効果が限定的

## カスタマイズ方法

### 保有株式管理

保有株は `data/my_stock.csv` で管理します。このCSVファイルを編集することで、銘柄の追加、数量変更、購入価格変更が可能です。システムはCSVの内容を読み込んで自動的に分析・監視を行います。

`data/my_stock.csv` の例:

```csv
code,name,quantity,purchase_price,purchase_date,sector
7974.T,任天堂,30,8000,2024-06-01,ゲーム
1878.T,大東建託,50,2000,2024-06-01,不動産
7203.T,トヨタ自動車,100,2500,2024-06-01,自動車
```

### リスク管理パラメータ（`python/config.py`）

リスク管理に関するパラメータは `python/config.py` で設定できます。

- ストップロス幅（%）: `self.max_loss_percent = 3.0`
- 利確幅（%）: `self.take_profit_percent = 8.0`
- 暴落アラート閾値（%）: `self.crash_threshold = -3.0`

## リアルタイム監視・分析フロー

システムは以下のフローでリアルタイム監視と分析を行います。

```mermaid
flowchart TD
    A[CSV 読み込み: my_stock.csv] --> B[株価取得: 2分周期]
    B --> C{価格変動確認}
    C -->|下落 >= 3%| D[アラート出力-ログ, Slack ]
    C -->|正常| E[データ保存 -SQLite]
    E --> F[MACD / ボリンジャー計算]
    F --> G[ポートフォリオ指標計算]
    G --> H[レポート生成 & 保存]
    H --> I[テクニカル指標グラフ生成 & 保存]
```

- 2分ごとに株価を取得して SQLite に保存します。
- 下落が閾値以上の場合、アラートを出力します。
- ポートフォリオ分析やテクニカル指標の計算も自動実行されます。

## アラート条件表

| 条件 | 内容 | 出力形式 |
|---|---|---|
| 価格下落 ≥ -3% | 暴落アラート | ログ / Slack |
| 連続2本下落 | ダマシ回避 | ログ |
| ストップロス達成（-max_loss%） | 強制売却候補 | ログ / レポート |
| 利確達成（+take_profit%） | 利益確定候補 | ログ / レポート |

## 閾値一覧表（`python/config.py` 設定例）

| パラメータ | 値 | 説明 |
|---|---|---|
| max_loss_percent | 3.0 | 許容損失の最大割合 |
| take_profit_percent | 8.0 | 利確の目標割合 |
| crash_threshold | -3.0 | 暴落アラート発生割合 |
| risk_free_rate | 0.1% | シャープレシオ計算用無リスク金利 |

## 定例タスク

結果はslackに通知

### 日常チェック（5分）

- 保有株状況確認: `python3 trading/every_stock_BuySell_timing.py ../data/my_stock.csv`
- 重要シグナル確認: `python3 watch/watch.py`

### 週次分析（30分）

- 売買タイミング分析: `python3 trading/every_stock_BuySell_timing.py ../data/my_stock.csv`
- 分析結果確認: `cat ../data/report/summary/summary_report_*.txt`

### 月次評価（1時間）

- 長期パフォーマンス分析: `python3 trading/every_stock_BuySell_timing.py ../data/my_stock.csv --period 6mo`
- ポートフォリオ再構築検討: 分析結果を基に銘柄入れ替えを検討します。

### 年次タスク(毎年12/31に実施)

- `my_stock.db`を`data/archive/YYYY_myStock.csv` にbump

### ポートフォリオ総合分析・グラフ生成

`python3 analysis/portfolio_analyzer.py` を実行すると、以下の結果が生成されます。

- レポート生成: `../data/my_portfolio_analysis.txt`
- MACD・ボリンジャーバンドグラフ: `../data/plots/*.png`

## 分析フローまとめ

1. CSV 読み込み → 保有株一覧取得
2. 株価取得（Yahoo Finance / 2分周期）
3. リアルタイム監視（暴落・ダマシ回避）
4. 売買タイミング分析（ストップロス / 利確 / MACD・ボリンジャー）
5. ポートフォリオ指標計算（リターン・ボラティリティ・シャープレシオ・ドローダウン・VaR）
6. レポート生成 & 保存
7. テクニカル指標グラフ生成 & 保存
