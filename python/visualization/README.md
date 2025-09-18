# 可視化モジュールガイド

## 📁 **ディレクトリ概要**

`python/visualization/`は、株式データや分析結果を視覚的に表現するためのモジュールを管理するディレクトリです。チャート生成、指標プロット、チャート表示などの機能を提供します。

## 🔧 **モジュール一覧**

### ****`init.py`**

- **用途**: パッケージの初期化ファイル
- **内容**: モジュールのインポート設定
- **使用方法**: 自動的に読み込まれる

### **`generate_all_charts.py`**

- **用途**: 全てのチャートを一括生成
- **機能**: 指定された銘柄リストやポートフォリオに対して、必要な全てのチャート（株価、テクニカル指標など）を自動で生成し、保存します。

### **`plot_indicators.py`**

- **用途**: テクニカル指標のプロット
- **機能**: 株価データにRSI、移動平均、ボリンジャーバンドなどのテクニカル指標を重ねてプロットし、視覚的に分かりやすいチャートを生成します。

### **`stock_chart_visualizer.py`**

- **用途**: 個別株チャートの可視化
- **機能**: 特定の銘柄の株価データを詳細に可視化するためのクラスや関数を提供します。期間指定、イベント表示などの機能を含みます。

### **`view_charts.py`**

- **用途**: 生成されたチャートの表示
- **機能**: 生成されたチャート画像ファイルを読み込み、ユーザーが簡単に閲覧できるインターフェースを提供します。

## 🚀 **使用方法**

### **基本的なインポート**

```python
# 全可視化ユーティリティをインポート
from visualization import generate_all_charts, plot_indicators, stock_chart_visualizer, view_charts

# 特定の機能のみインポート
from visualization.generate_all_charts import ChartGenerator
from visualization.plot_indicators import plot_stock_with_indicators
```

### **全チャートの一括生成**

```python
from visualization.generate_all_charts import ChartGenerator

# チャートジェネレーターの初期化
chart_generator = ChartGenerator(output_dir="data/chartImg")

# 全チャートの生成
chart_generator.generate_charts_for_portfolio(portfolio_data)
```

### **指標付きチャートのプロット**

```python
from visualization.plot_indicators import plot_stock_with_indicators
import pandas as pd

# サンプルデータ（DataFrame形式）
stock_data = pd.DataFrame({
    'Date': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']),
    'Open': [100, 101, 102],
    'High': [102, 103, 104],
    'Low': [99, 100, 101],
    'Close': [101, 102, 103],
    'Volume': [1000, 1200, 1100]
}).set_index('Date')

# 指標付きチャートのプロット
plot_stock_with_indicators(stock_data, code="7974.T", name="任天堂", output_path="data/plots/7974.T_indicators.png")
```

### **チャートの表示**

```python
from visualization.view_charts import ChartViewer

# チャートビューアの初期化
viewer = ChartViewer(chart_dir="data/chartImg")

# チャートの表示
viewer.display_charts()
```

## ⚙️ **設定とカスタマイズ**

### **チャート生成設定のカスタマイズ**

```python
# config.pyでの設定例
CHART_SETTINGS = {
    'output_directory': 'data/chartImg',
    'chart_type': 'candlestick', # candlestick, line
    'include_indicators': ['RSI', 'MACD', 'BollingerBands'],
    'date_range': '1Y' # 1Y, 3M, ALL
}
```

## 📚 **関連ドキュメント**

- メインREADME: `../README.md`
- ユーティリティモジュール: `../utils/README.md`
- 設定ファイル: `../config.py`

---

**注意**: 可視化モジュールは、データの解釈を助ける強力なツールです。生成されるチャートが正確で分かりやすいことを確認してください。
