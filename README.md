# 株式投資分析・運用システム

## **概要**

保有株式のポートフォリオ分析、売買タイミングの判定、リスク管理を行うPythonベースの投資支援システムです。

## 📊 **現在の保有株式**

`data/my_stock.csv`に記載

## **セットアップ**

### **1. 環境準備**

```bash
# プロジェクトディレクトリに移動
cd /Users/niwa_kazuhiro/Documents/PrivateDevelop/stockManegement

# 仮想環境の有効化（推奨）
source venv/bin/activate

# 必要なパッケージのインストール
pip install -r requirements.txt
```

### **2. 構造**

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

## 📈 **基本的な使い方**

### **1. 保有株式の分析**

```bash
cd python

# 保有株式の売買タイミングを分析
python3 every_stock_BuySell_timing.py ../data/my_stock.csv

# 分析期間を指定（例：6ヶ月）
python3 every_stock_BuySell_timing.py ../data/my_stock.csv --period 6mo
```

### **2. チャートの作成・確認**

```bash
# 保有株式のチャートを作成
python3 stock_chart_visualizer.py

# 作成されたチャートを確認
python3 view_charts.py
```

### **3. ポートフォリオ分析**

```bash
# ポートフォリオ全体の分析
python3 portfolio_analyzer.py

# 売買ルールの検証
python3 trading_rules.py
```

### **4. リアルタイム監視**

```bash
# 日次監視（推奨）
python3 watch.py
```

## 🎯 **売買タイミングの理解**

### **買いシグナル**

- **++パターン**: 連続上昇（ゴールデンクロス）
- **RSI過売り**: RSI 30以下からの反転
- **価格安値圏**: 長期移動平均線の90%以下

### **売りシグナル**

- **--パターン**: 連続下降（デッドクロス）
- **RSI過買い**: RSI 70以上からの反転
- **利確**: 10%利益達成での自動売却
- **ストップロス**: 5%損失での自動売却

## 📊 **分析結果の読み方**

### **重要な指標**

| 指標 | 良い値 | 悪い値 | 説明 |
|------|--------|--------|------|
| **総リターン** | +5%以上 | -5%以下 | 期間中の収益率 |
| **年率リターン** | +10%以上 | -10%以下 | 年間換算の収益率 |
| **ボラティリティ** | 20%以下 | 40%以上 | 価格変動の激しさ |
| **シャープレシオ** | 1.0以上 | 0.5以下 | リスク調整後リターン |
| **最大ドローダウン** | -10%以内 | -20%以下 | 最大の損失幅 |
| **勝率** | 60%以上 | 40%以下 | 利益が出る取引の割合 |

### **分散効果の評価**

- 平均相関係数:
  - 0.3未満 → ✅ 良好な分散効果
  - 0.3-0.6 → ⚠️ 中程度の分散効果  
  - 0.6以上 → ❌ 分散効果が限定的

## 🔧 **カスタマイズ方法**

### **保有株式管理**

保有株は CSV で管理します。

`data/my_stock.csv`

```csv
code,name,quantity,purchase_price,purchase_date,sector
7974.T,任天堂,30,8000,2024-06-01,ゲーム
1878.T,大東建託,50,2000,2024-06-01,不動産
7203.T,トヨタ自動車,100,2500,2024-06-01,自動車
```

- 銘柄追加・数量変更・購入価格変更はこの CSV を編集
- CSV を読み込んで分析・監視が自動で行われます

⸻

### **リスク管理パラメータ（`config.py`）**

- ストップロス幅（%）
  - self.max_loss_percent = 3.0

- 利確幅（%）
  - self.take_profit_percent = 8.0

- 暴落アラート閾値（%）
  - self.crash_threshold = -3.0

---

## **リアルタイム監視・分析フロー**

```mermaid
flowchart TD
    A[CSV 読み込み: my_stock.csv] --> B[株価取得: 2分周期]
    B --> C{価格変動確認}
    C -->|下落 >= 3%| D[アラート出力 (ログ / Slack / LINE)]
    C -->|正常| E[データ保存 (SQLite)]
    E --> F[MACD / ボリンジャー計算]
    F --> G[ポートフォリオ指標計算]
    G --> H[レポート生成 & 保存]
    H --> I[テクニカル指標グラフ生成 & 保存]
```

- 2分ごとに株価を取得して SQLite に保存
- 下落が閾値以上ならアラート
- ポートフォリオ分析・テクニカル指標計算も自動実行

---

## **アラート条件表**

|条件|内容|出力形式|
|--|--|--|
|価格下落 ≥ -3%	|暴落アラート|	ログ / Slack / LINE|
|連続2本下落	|ダマシ回避|	ログ|
|ストップロス達成（-max_loss%）	|強制売却候補|	ログ / レポート|
|利確達成（+take_profit%）|	利益確定候補|	ログ / レポート|

---

## **閾値一覧表（`config.py` 設定例）**

|パラメータ|値|説明|
|---|---|---|
|max_loss_percent|3.0|許容損失の最大割合|
|take_profit_percent|8.0|利確の目標割合|
|crash_threshold|-3.0|暴落アラート発生割合 |
|risk_free_rate|0.1%|シャープレシオ計算用無リスク金利 |

---

## **実行コマンド例**

### 日常チェック（5分）

- 保有株状況確認
`python3 trading/every_stock_BuySell_timing.py ../data/my_stock.csv`

- 重要シグナル確認
`python3 watch/watch.py`

### 週次分析（30分）

- 売買タイミング分析
`python3 trading/every_stock_BuySell_timing.py ../data/my_stock.csv`

-分析結果確認
`cat ../data/report/summary/summary_report_*.txt`

### 月次評価（1時間）

- 長期パフォーマンス分析
`python3 trading/every_stock_BuySell_timing.py ../data/my_stock.csv --period 6mo`

- ポートフォリオ再構築検討
- 分析結果を基に銘柄入れ替え検討

### ポートフォリオ総合分析・グラフ生成

`python3 analysis/portfolio_analyzer.py`

- レポート生成: ../data/my_portfolio_analysis.txt
- MACD・ボリンジャーバンドグラフ: ../data/plots/*.png

---

### **分析フローまとめ**

1. CSV 読み込み → 保有株一覧取得
2. 株価取得（Yahoo Finance / 2分周期）
3. リアルタイム監視（暴落・ダマシ回避）
4. 売買タイミング分析（ストップロス / 利確 / MACD・ボリンジャー）
5. ポートフォリオ指標計算（リターン・ボラティリティ・シャープレシオ・ドローダウン・VaR）
6. レポート生成 & 保存
7. テクニカル指標グラフ生成 & 保存

---

### memo

3. **より高度な分析指標の追加**

#### **実装までのロードマップ**

- **目的**:スイングトレードを行うにあたって
  - **急落や乱高下に対応**
  - **数日スパンでのトレンド把握**

1. **リアルタイム監視 (`watch/`)**
   1. 現状
      - `watch.py` が「株価を定期取得しDBへ格納」
   2. 今後の方針
        - 最初は `yfinance` を分単位で叩く擬似リアルタイム でOK
        - 将来的に証券会社APIやWeb-socketが使えるようになれば差し替え可能
        - `dailyAggregator.py` が 分足 → 日足 を自動集計
        - `analyze.py` が 一定閾値（例: -5%急落）検出 → アラート
   3. 目標
        - 「2分ごとに株価を取得 → SQLite保存 → -3%以上下落でログ出力」
   4. 急落検知について
        - **基本**
          - リアルタイム監視の役割は「想定外の暴落（例：数分で-3%）を捕捉して通知」
          - スイングは1日単位が軸なので、あくまで 損失限定の安全弁 という立ち位置
        - **拡張**
          - 日中で±2～3%以上を何度も行き来する**乱高下対応**
            - ボラティリティ監視
              - 直近N本（例：30分間）の分足データで標準偏差（σ）を計算
              - σが通常より大きければ「ボラティリティ警告」
              - RSIやボリンジャーバンドと組み合わせて「行き過ぎ」を見極める
              - ボラティリティフィルタ
                - ATR（平均真の変動幅）や標準偏差を使って「その日の変動が大きすぎるときは見送り」。
                - コカコーラの 7/29〜8/5 のような乱高下を「ノーエントリー」にできる。
            - ダマシ回避
              - 一時的な-3% → 直後に+3% のような「ダマシ急落」も多い
              - 1本の足ではなく連続2本で同方向確認してから通知
            - **具体的な乱高下対策**
              - フィルター期間を設ける
                - 例えば「前回売買から3日間は新規エントリー禁止」
              - ボラティリティ（標準偏差σ）チェック
                - σが大きすぎるときは「ノートレード」として休む
          - **数日間の予測・分析**
            - 「リアルタイム監視」より「分析（日足ベース）」。
              - MACD / RSI（数日スパンのトレンド指標）
              - ゴールデンクロス / デッドクロスが出たら「上昇／下降傾向」アラート
              - ボリンジャーバンド
              - ±2σ突破 → 過熱感（買われすぎ / 売られすぎ）
              - 出来高分析（VWAPなど）
              - 出来高を伴う動きかどうか確認
            - この部分は `weeklyAnalysis.py` や `portfolio_analyzer.py` に組み込んで、週次のtxtレポートやチャートで確認する。
            - 日足だけでなく、3日移動平均 or MACD を見て「短期トレンド」を補助指標にする
              - 例：ゴールデンクロス（++）が出ても、MACDがまだマイナス圏なら見送り,RSIが70を超えているなら「買われすぎ」でエントリーしない

2. **より高度な分析指標の追加 (`utils/indicator.py`)**
   1. 現状
      - 移動平均やRSI程度を想定
   2. 方針
      - 最初に追加するのは「MACD」「ボリンジャーバンド」-> 短期トレードに有効
      - 将来的に「出来高分析（VWAP）」「モメンタム指標」-> 中長期ポートフォリオに有効
      - 週次・月次に耐えられるよう 日足の加工関数を整備-> `portfolio_analyzer.py` で利用
   3. 損切りルールの強化
      - 現状ストップロスは「-5%」など固定
      - 改善案
        - ATR（平均値幅）を使って「ボラティリティに応じた損切り幅」を設定
        - 乱高下が激しいときは損切り幅を広げ、通常時は狭める
   4. 利確の柔軟化
      - 今は「`-`シグナル or ストップロス」でしか手仕舞いしない
      - 改善案
        - 「+3% 到達したら半分利確」
        - 「移動平均線から一定以上乖離したら利確」
   5. 利益・損失幅の閾値を設定
      - 売却条件に「±○%超えたらのみ確定」とする。
      - たとえば ±1%以内のシグナルは無視。
      - ノイズでの往復を防ぐ。
      - ストップロスは -5% のまま、利確は 2〜3% にしてもよい。

3. **アラートの追加 (`utils/alert.py`)**
   1. 現状
         - まだ未接続
         - Slack/LINE通知予定
   2. 方針
         - 第一段階：print/logging に出力（テスト確認）
         - 第二段階：Slack Web-hook → すぐ実用可
         - 第三段階：LINE Notify API → モバイル通知
   3. 役割分担
         - `alert.py` は通知方法をラップ
         - 監視・売買ロジックは alertの呼び出しだけ
   4. 拡張機能
         - シグナルのフィルタリング（確認遅延）
           - たとえば「クロスが出た次の日も同じ傾向が続いたら確定」とする。
           - `++` が出ても翌日すぐ`-` が出たらスルー（ノートレード）。
           - クロス発生直後の**ダマシ**を回避できます。
           - 「1日遅れで判断する」イメージ。
         - 最低保有期間ルール
           - 一度買ったら「最低でもX日間は保有する」ようにする。
             - 例: 3日間は売らない → 短期乱高下に振り回されにくくなる。
             - スイングなら「3〜5日ホールド」を条件にすると自然。
           - 複数条件でのシグナル確認
             - 1つのシグナル（++）だけでなく、移動平均乖離率や出来高など補助指標も条件に加える。
             - 例えば
               - ++ かつ 5日線が上向き
               - ++ かつ RSI < 70

```python
# 実装イメージ
（例：1日確認遅延 + ±1%閾値）

# 仮シグナル発生
if signal == "buy" and not position:
    # 翌日も同じシグナルかチェック
    if next_day_signal == "buy" and price_change > 0.01:
        position = True
        buy_price = price
        trades.append(f"{date}: {price}円 - エントリー")
```

---

```
stockManegement//
├── data
│   ├── .DS_Store
│   ├── archive
│   ├── chartImg
│   │   ├── 1878_T_大東建託.png
│   │   ├── 2579_T_COCA-COLA BOTTLERS JAPAN HLDGS .png
│   │   ├── 2730_T_EDION CORP.png
│   │   ├── 3003_T_HULIC CO LTD.png
│   │   ├── 3543_T_KOMEDA HOLDINGS CO LTD.png
│   │   ├── 3778_T_SAKURA INTERNET INC.png
│   │   ├── 7803_T_BUSHIROAD INC.png
│   │   ├── 7974_T_任天堂.png
│   │   ├── 8035_T_東京エレクトロン.png
│   │   ├── 9082_T_DAIWA MOTOR TRANSPORTATION CO.png
│   │   ├── 9202_T_ANA HOLDINGS INC.png
│   │   ├── 9347_T_NIPPON KANZAI HOLDINGS CO LTD.png
│   │   ├── 9434_T_SOFTBANK CORP..png
│   │   ├── 9697_T_CAPCOM CO LTD.png
│   │   ├── trading_summary_codes.txt
│   │   └── trading_summary_my_stock.txt
│   ├── my_portfolio_analysis.txt
│   ├── my_stock.csv
│   ├── plots
│   │   ├── 2579.T_indicators.png
│   │   ├── 2730.T_indicators.png
│   │   ├── 3003.T_indicators.png
│   │   ├── 3543.T_indicators.png
│   │   ├── 3778.T_indicators.png
│   │   ├── 7803.T_indicators.png
│   │   ├── 7974.T_indicators.png
│   │   ├── 8035.T_indicators.png
│   │   ├── 9202.T_indicators.png
│   │   ├── 9347.T_indicators.png
│   │   ├── 9434.T_indicators.png
│   │   └── 9697.T_indicators.png
│   ├── portfolio_analysis_20250908_101811.txt
│   ├── portfolio_analysis_20250908_103046.txt
│   ├── portfolio_analysis_20250908_103207.txt
│   ├── portfolio_analysis_20250908_103232.txt
│   ├── practice
│   │   ├── charts
│   │   │   ├── 4503_T_アステラス製薬.png
│   │   │   ├── 6367_T_ダイキン工業.png
│   │   │   ├── 6752_T_パナソニック.png
│   │   │   ├── 6758_T_ソニーグループ.png
│   │   │   ├── 6861_T_キーエンス.png
│   │   │   ├── 7203_T_トヨタ自動車.png
│   │   │   ├── 7974_T_任天堂.png
│   │   │   ├── 8306_T_三菱UFJフィナンシャル・グループ.png
│   │   │   ├── 9433_T_KDDI.png
│   │   │   ├── 9984_T_ソフトバンクグループ.png
│   │   │   ├── demo_7203_T_トヨタ自動車.png
│   │   │   └── trading_summary_portfolio_practice.txt
│   │   ├── portfolio_beginner.csv
│   │   ├── portfolio_diversified.csv
│   │   ├── portfolio_growth.csv
│   │   ├── portfolio_practice.csv
│   │   ├── portfolio_stable.csv
│   │   ├── portfolio_template.csv
│   │   └── portfolio_with_notes.csv
│   ├── quarterly_analysis.csv
│   ├── README.md
│   └── report
│       ├── detailed
│       │   ├── detailed_report_20250903_131214.txt

│       └── summary
│           ├── summary_report_20250903_131214.txt

│           └── summary_report_20250908_155859.txt
├── log
│   ├── analysis
│   ├── db
│   ├── README.md
│   ├── trading
│   ├── utils
│   ├── visualization
│   └── watch
├── main.py
├── makefile
├── python
│   ├── __init__.py
│   ├── analysis
│   │   ├── __init__.py
│   │   ├── analyze_my_stock.py
│   │   ├── data_collector.py
│   │   ├── portfolio_analyzer.py
│   │   └── README.md
│   ├── config.py
│   ├── data
│   │   ├── analysis_result.txt
│   │   └── portfolio_analysis_20250908_122913.txt
│   ├── db
│   │   ├── dump_csv.py
│   │   ├── README.md
│   │   └── stock.db
│   ├── init_database.py
│   ├── python
│   ├── trading
│   │   ├── __init__.py
│   │   ├── buy_and_sell_stock.py
│   │   ├── every_stock_BuySell_timing.py
│   │   ├── README.md
│   │   └── trading_rules.py
│   ├── utils
│   │   ├── __init__.py
│   │   ├── alert.py
│   │   ├── indicators.py
│   │   └── README.md
│   ├── visualization
│   │   ├── __init__.py
│   │   ├── generate_all_charts.py
│   │   ├── plot_indicators.py
│   │   ├── README.md
│   │   ├── stock_chart_visualizer.py
│   │   └── view_charts.py
│   └── watch
│       ├── __init__.py
│       ├── analyze.py
│       ├── dailyAggregator.py
│       ├── README.md
│       └── watch.py
├── README.md
└── requirements.txt

```

[ ]:analysis
  [ ]: analyze_my_stock.py
  [x]: data_collecter.py
  [ ]:portfolio_analyzer.py

[x]:trading
  [x]:buy_and_sell_stock.py
  [x]:every_stock_BuySell_timing.py

[x]:visualization
  [x]:generate_all_charts.py
  [x]:plot_indicators.py
  [x]:stock_chart_visualizer.py
  [ ]:view_charts.py

[ ]:utils
  [ ]:alert.py
  [ ]:indicators.py

[ ]:watch
  [ ]:analyze.py
  [ ]: dailyAggregator.py
  [ ]:watch.py