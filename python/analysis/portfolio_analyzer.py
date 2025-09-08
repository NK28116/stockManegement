import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import ta
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db/stock.db")
RESULT_DIR = os.path.join(os.path.dirname(__file__), "../data")
os.makedirs(RESULT_DIR, exist_ok=True)

class PortfolioAnalyzer:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    def get_portfolio(self, portfolio_name='practice'):
        """保有株式情報を取得"""
        query = """
        SELECT ph.id, ph.code, s.name, s.sector, ph.quantity, ph.purchase_price, ph.purchase_date
        FROM portfolio_holdings ph
        JOIN stocks s ON ph.code = s.code
        WHERE ph.portfolio_name = ?
        """
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=(portfolio_name,))
        return df

    def get_stock_prices(self, code):
        """特定銘柄の株価取得"""
        query = """
        SELECT date, open, high, low, close, volume
        FROM stock_prices
        WHERE code = ?
        ORDER BY date
        """
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=(code,))
            df['date'] = pd.to_datetime(df['date'])
        return df

    def calculate_technical_indicators(self, price_df):
        """テクニカル指標を計算"""
        indicators = pd.DataFrame(index=price_df.index)
        indicators['Close'] = price_df['close']
        
        # Bollinger Bands
        bb = ta.volatility.BollingerBands(close=price_df['close'], window=20, window_dev=2)
        indicators['bb_middle'] = bb.bollinger_mavg()
        indicators['bb_upper'] = bb.bollinger_hband()
        indicators['bb_lower'] = bb.bollinger_lband()
        
        # MACD
        macd = ta.trend.MACD(close=price_df['close'])
        indicators['macd'] = macd.macd()
        indicators['macd_signal'] = macd.macd_signal()
        indicators['macd_diff'] = macd.macd_diff()
        
        return indicators

    def save_analysis(self, portfolio_df, indicators_dict):
        """分析結果をテキスト保存"""
        filename = f"portfolio_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join(RESULT_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("=== Portfolio Holdings ===\n")
            f.write(portfolio_df.to_string(index=False))
            f.write("\n\n=== Technical Indicators ===\n")
            for code, ind in indicators_dict.items():
                f.write(f"\n--- {code} ---\n")
                f.write(ind.tail(5).to_string())
        print(f"分析結果を保存: {filepath}")

    def plot_indicators(self, price_df, indicators, code):
        """株価 + テクニカル指標グラフ描画"""
        fig, ax = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        
        # 株価 + Bollinger Bands
        ax[0].plot(price_df['date'], price_df['close'], label='Close')
        ax[0].plot(price_df['date'], indicators['bb_middle'], label='BB Middle', linestyle='--', color='orange')
        ax[0].plot(price_df['date'], indicators['bb_upper'], label='BB Upper', linestyle='--', color='green')
        ax[0].plot(price_df['date'], indicators['bb_lower'], label='BB Lower', linestyle='--', color='red')
        ax[0].set_title(f"{code} Price + Bollinger Bands")
        ax[0].legend()
        
        # MACD
        ax[1].plot(price_df['date'], indicators['macd'], label='MACD', color='blue')
        ax[1].plot(price_df['date'], indicators['macd_signal'], label='Signal', color='red')
        ax[1].bar(price_df['date'], indicators['macd_diff'], label='MACD Diff', color='gray')
        ax[1].set_title(f"{code} MACD")
        ax[1].legend()
        
        plt.tight_layout()
        plt.show()


def analyze_portfolio():
    analyzer = PortfolioAnalyzer()
    
    portfolio_df = analyzer.get_portfolio(portfolio_name='practice')
    indicators_dict = {}
    
    for _, row in portfolio_df.iterrows():
        code = row['code']
        price_df = analyzer.get_stock_prices(code)
        if price_df.empty:
            continue
        indicators = analyzer.calculate_technical_indicators(price_df)
        indicators_dict[code] = indicators
        analyzer.plot_indicators(price_df, indicators, code)
    
    analyzer.save_analysis(portfolio_df, indicators_dict)
    print("✅ ポートフォリオ分析完了")


if __name__ == "__main__":
    analyze_portfolio()