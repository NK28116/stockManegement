
# ユーティリティモジュールガイド

## 📁 **ディレクトリ概要**

`python/utils/`は、株式投資分析システムで使用する共通のユーティリティ関数とクラスを管理するディレクトリです。

## 🔧 **モジュール一覧**

### ****`init.py`**

- **用途**: パッケージの初期化ファイル
- **内容**: モジュールのインポート設定
- **使用方法**: 自動的に読み込まれる

### **`alert.py`**

- **用途**: アラート・通知機能
- **機能**: 価格変動、売買シグナル、リスク管理の通知

### **`indicators.py`**

- **用途**: テクニカル指標の計算
- **機能**: RSI、移動平均、ボリンジャーバンド等の計算

### **`logger.py`**

- **用途**: ロギング機能
- **機能**: アプリケーションのログ出力設定と管理

### **`report.py`**

- **用途**: レポート生成機能
- **機能**: 分析結果や取引履歴のレポート作成

## 📊 **`alert.py` - アラート機能**

### **主要クラス**

#### **PriceAlert（価格アラート）**

```python
from utils.alert import PriceAlert

# アラートの作成
alert = PriceAlert(
    code="7974.T",
    threshold_price=7500,
    alert_type="below"  # below: 下回った時, above: 上回った時
)

# アラートの確認
if alert.check_condition(current_price):
    alert.send_notification()
```

#### **PortfolioAlert（ポートフォリオアラート）**

```python
from utils.alert import PortfolioAlert

# ポートフォリオ全体のアラート
portfolio_alert = PortfolioAlert(
    max_loss_threshold=-0.05,  # 5%損失
    max_gain_threshold=0.10    # 10%利益
)

# アラートの確認
portfolio_alert.check_portfolio_status(portfolio_data)
```

### **アラートの種類**

| アラートタイプ | 説明 | 使用例 |
|----------------|------|--------|
| **価格アラート** | 特定価格の突破・下回り | ストップロス、利確 |
| **変動率アラート** | 急激な価格変動 | 暴落・暴騰の検知 |
| **テクニカルアラート** | 指標の変化 | RSI過買い・過売り |
| **ポートフォリオアラート** | 全体の状況 | リスク管理 |

### **設定例**

```python
# 設定ファイルでのアラート設定
ALERT_CONFIG = {
    'price_change_threshold': 0.05,    # 5%変動
    'volume_spike_threshold': 3.0,     # 出来高3倍
    'rsi_overbought': 70,             # RSI過買い
    'rsi_oversold': 30                 # RSI過売り
}
```

## **indicators.py - テクニカル指標**

### **利用可能な指標**

#### **移動平均（Moving Average）**

```python
from utils.indicators import calculate_moving_average

# 単純移動平均
sma_20 = calculate_moving_average(prices, window=20)

# 指数移動平均
ema_20 = calculate_moving_average(prices, window=20, method='exponential')
```

#### **RSI（相対力指数）**

```python
from utils.indicators import calculate_rsi

# RSI計算（14日）
rsi_14 = calculate_rsi(prices, window=14)

# 過買い・過売り判定
is_overbought = rsi_14 > 70
is_oversold = rsi_14 < 30
```

#### **ボリンジャーバンド**

```python
from utils.indicators import calculate_bollinger_bands

# ボリンジャーバンド計算
upper, middle, lower = calculate_bollinger_bands(
    prices, 
    window=20, 
    std_dev=2
)

# バンド位置の判定
is_upper_band = current_price > upper[-1]
is_lower_band = current_price < lower[-1]
```

#### **MACD**

```python
from utils.indicators import calculate_macd

# MACD計算
macd_line, signal_line, histogram = calculate_macd(
    prices, 
    fast=12, 
    slow=26, 
    signal=9
)

# ゴールデンクロス・デッドクロス判定
golden_cross = macd_line[-1] > signal_line[-1] and macd_line[-2] <= signal_line[-2]
dead_cross = macd_line[-1] < signal_line[-1] and macd_line[-2] >= signal_line[-2]
```

### **カスタム指標の作成**

```python
from utils.indicators import BaseIndicator

class CustomIndicator(BaseIndicator):
    """カスタムテクニカル指標"""
    
    def calculate(self, data, **params):
        # カスタム計算ロジック
        result = self._custom_calculation(data, **params)
        return result
    
    def _custom_calculation(self, data, **params):
        # 実装例：価格と出来高の組み合わせ指標
        price_change = data['close'].pct_change()
        volume_ratio = data['volume'] / data['volume'].rolling(20).mean()
        
        return price_change * volume_ratio
```

## 🚀 **使用方法**

### **基本的なインポート**

```python
# 全ユーティリティをインポート
from utils import alert, indicators

# 特定の機能のみインポート
from utils.alert import PriceAlert
from utils.indicators import calculate_rsi
```

### **アラートシステムの統合**

```python
# ポートフォリオ分析での使用例
def analyze_portfolio_with_alerts(portfolio_data):
    # 分析実行
    analysis_result = analyze_portfolio(portfolio_data)
    
    # アラートチェック
    alerts = []
    
    for stock in portfolio_data:
        # 価格アラート
        price_alert = PriceAlert(stock['code'], stock['stop_loss'])
        if price_alert.check_condition(stock['current_price']):
            alerts.append("価格アラート: {stock['code']}")
        
        # RSIアラート
        rsi = calculate_rsi(stock['prices'])
        if rsi[-1] > 70:
            alerts.append("RSI過買い: {stock['code']}")
    
    return analysis_result, alerts
```

### **テクニカル指標の活用**

```python
# 売買シグナルの生成
def generate_trading_signals(stock_data):
    signals = []
    
    # RSI判定
    rsi = calculate_rsi(stock_data['close'])
    if rsi[-1] < 30:
        signals.append({
            'type': 'BUY',
            'reason': 'RSI過売り',
            'confidence': 0.8
        })
    
    # 移動平均判定
    sma_20 = calculate_moving_average(stock_data['close'], 20)
    sma_50 = calculate_moving_average(stock_data['close'], 50)
    
    if sma_20[-1] > sma_50[-1] and sma_20[-2] <= sma_50[-2]:
        signals.append({
            'type': 'BUY',
            'reason': 'ゴールデンクロス',
            'confidence': 0.9
        })
    
    return signals
```

## ⚙️ **設定とカスタマイズ**

### **アラート設定のカスタマイズ**

```python
# config.pyでの設定例
ALERT_SETTINGS = {
    'enabled': True,
    'notification_method': 'console',  # console, email, slack
    'price_thresholds': {
        '7974.T': {'upper': 9000, 'lower': 7000},
        '1878.T': {'upper': 2500, 'lower': 1500}
    },
    'rsi_thresholds': {'overbought': 75, 'oversold': 25}
}
```

### **指標パラメータの調整**

```python
# 指標計算のパラメータ調整
INDICATOR_PARAMS = {
    'rsi_window': 14,
    'moving_average_windows': [5, 20, 50, 200],
    'bollinger_std_dev': 2.0,
    'macd_params': {'fast': 12, 'slow': 26, 'signal': 9}
}
```

## 🔍 **デバッグとテスト**

### **ログ出力の確認**

```python
import logging

# ログレベルの設定
logging.basicConfig(level=logging.DEBUG)

# ユーティリティのログ確認
logger = logging.getLogger('utils.indicators')
logger.debug('RSI計算開始')
```

### **単体テスト**

```python
# テストファイルでの使用例
def test_rsi_calculation():
    test_prices = [100, 101, 99, 102, 98, 103, 97]
    rsi = calculate_rsi(test_prices, window=5)
    
    assert len(rsi) == len(test_prices)
    assert 0 <= rsi[-1] <= 100
```

## 📚 **関連ドキュメント**

- メインREADME: `../docs/README.md`
- ポートフォリオ分析: `../portfolio_analyzer.py`
- 売買ルール: `../trading_rules.py`
- 設定ファイル: `../config.py`

---

**注意**: ユーティリティ関数は他のモジュールから頻繁に使用されるため、変更時は十分なテストを行ってください。
