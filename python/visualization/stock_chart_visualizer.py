"""
株価チャート可視化ツール
全銘柄の売買タイミングを表示
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import os
import sys
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')
import shutil

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from python.trading.trading_rules import ImprovedTradingRules

# Set font with fallbacks - suppress font warnings
import matplotlib
matplotlib.rcParams['font.family'] = 'Hiragino Sans'  # 日本語対応（macOS標準）
matplotlib.rcParams['axes.unicode_minus'] = False     # マイナス記号の文字化け対策
# Suppress font warning messages
import logging
matplotlib_logger = logging.getLogger('matplotlib.font_manager')
matplotlib_logger.setLevel(logging.ERROR)

class StockChartVisualizer:
    """株価チャート可視化クラス"""
    
    def __init__(self, period="3mo"):
        self.period = period
        self.trading_rules = ImprovedTradingRules()
        self.output_dir = "../data/chartImg"  # 出力先を変更
        os.makedirs(self.output_dir, exist_ok=True)

    def clean_output_dir(self):
        """出力先の既存PNGを削除"""
        removed = 0
        for name in os.listdir(self.output_dir):
            if name.lower().endswith(".png"):
                try:
                    os.remove(os.path.join(self.output_dir, name))
                    removed += 1
                except Exception:
                    pass
        print(f"既存PNGを削除: {removed}件")

    def load_portfolio_stocks(self, portfolio_file: str) -> List[Dict]:
        """ポートフォリオファイルから株式リストを読み込み"""
        try:
            # 実際の運用用のcodes.csvを使用
            if portfolio_file == "codes.csv":
                portfolio_path = "../data/codes.csv"
            else:
                portfolio_path = f"../data/practice/{portfolio_file}"
            
            df = pd.read_csv(portfolio_path)
            
            stocks = []
            for _, row in df.iterrows():
                if pd.notna(row.get('code')) and str(row.get('code')).strip():
                    stocks.append({
                        'code': row['code'],
                        'name': row.get('name', row['code']),
                        'sector': row.get('sector', 'Unknown')
                    })
            
            print(f"ポートフォリオ読み込み完了: {len(stocks)}銘柄")
            return stocks
            
        except Exception as e:
            print(f"ポートフォリオ読み込みエラー: {e}")
            return []
    
    def fetch_stock_data(self, ticker: str) -> Optional[pd.DataFrame]:
        """株価データを取得"""
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=self.period)
            
            if df.empty:
                print(f"データが取得できません: {ticker}")
                return None
                
            print(f"データ取得完了: {ticker} - {len(df)}件")
            return df
            
        except Exception as e:
            print(f"データ取得エラー: {ticker} - {e}")
            return None
    
    def create_chart_with_signals(self, stock_info: Dict, df: pd.DataFrame, trades: List[Dict]) -> plt.Figure:
        """売買シグナル付きチャートを作成"""
        
        # Figure setup
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), height_ratios=[3, 1])
        fig.suptitle(f"{stock_info['name']} ({stock_info['code']}) - 売買タイミング分析", fontsize=16, fontweight='bold')
        
        # Price chart
        ax1.plot(df.index, df['Close'], linewidth=2, color='blue', label='終値', alpha=0.8)
        
        # Volume chart
        ax2.bar(df.index, df['Volume'], alpha=0.6, color='gray', label='出来高')
        
        # Add buy/sell signals
        buy_dates, buy_prices, sell_dates, sell_prices = [], [], [], []
        buy_reasons, sell_reasons = [], []
        
        for trade in trades:
            if 'date' in trade and 'price' in trade:
                trade_date = pd.to_datetime(trade['date'])
                
                if trade['action'] == 'BUY':
                    buy_dates.append(trade_date)
                    buy_prices.append(trade['price'])
                    buy_reasons.append(trade.get('reason', ''))
                    
                elif trade['action'] == 'SELL':
                    sell_dates.append(trade_date)
                    sell_prices.append(trade['price'])
                    sell_reasons.append(trade.get('reason', ''))
        
        # Plot buy signals
        if buy_dates:
            ax1.scatter(buy_dates, buy_prices, color='green', s=100, marker='^', 
                    label=f'買い ({len(buy_dates)}回)', zorder=5)
            
            # Add annotations for buy signals
            for i, (date, price, reason) in enumerate(zip(buy_dates, buy_prices, buy_reasons)):
                ax1.annotate(f'買い\n¥{price:.0f}', 
                        xy=(date, price), 
                        xytext=(10, 30), 
                        textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.7),
                        arrowprops=dict(arrowstyle='->', color='green'),
                        fontsize=9, ha='center')
        
        # Plot sell signals
        if sell_dates:
            ax1.scatter(sell_dates, sell_prices, color='red', s=100, marker='v', 
                    label=f'売り ({len(sell_dates)}回)', zorder=5)
            
            # Add annotations for sell signals
            for i, (date, price, reason) in enumerate(zip(sell_dates, sell_prices, sell_reasons)):
                profit_loss = ""
                for trade in trades:
                    if (trade.get('action') == 'SELL' and 
                        trade.get('date') == date.strftime('%Y-%m-%d') and 
                        'profit_loss_percent' in trade):
                        profit_loss = f"\n({trade['profit_loss_percent']:.1%})"
                        break
                
                ax1.annotate(f'売り\n¥{price:.0f}{profit_loss}', 
                        xy=(date, price), 
                        xytext=(10, -40), 
                        textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='lightcoral', alpha=0.7),
                        arrowprops=dict(arrowstyle='->', color='red'),
                        fontsize=9, ha='center')
        
        # Add moving averages
        if len(df) >= 25:
            ma5 = df['Close'].rolling(5).mean()
            ma25 = df['Close'].rolling(25).mean()
            ax1.plot(df.index, ma5, color='orange', alpha=0.7, linewidth=1, label='MA5')
            ax1.plot(df.index, ma25, color='purple', alpha=0.7, linewidth=1, label='MA25')
        
        # Chart formatting
        ax1.set_ylabel('価格 (円)', fontsize=12)
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        
        # Volume chart formatting
        ax2.set_xlabel('日付', fontsize=12)
        ax2.set_ylabel('出来高', fontsize=12)
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        
        # Rotate x-axis labels
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        return fig
    
    def generate_trading_summary(self, stock_info: Dict, trades: List[Dict], metrics: Dict) -> str:
        """取引サマリーを生成"""
        
        summary = [f"\n=== {stock_info['name']} ({stock_info['code']}) 取引サマリー ==="]
        
        if not metrics:
            summary.append("取引データがありません")
            return "\n".join(summary)
        
        # Basic metrics
        summary.append(f"総取引数: {metrics.get('total_trades', 0)}")
        summary.append(f"完了取引数: {metrics.get('completed_trades', 0)}")
        summary.append(f"勝率: {metrics.get('win_rate', 0):.1%}")
        summary.append(f"平均損益: {metrics.get('average_profit', 0):.2%}")
        summary.append(f"総リターン: {metrics.get('total_return', 0):.2%}")
        
        if metrics.get('max_profit', 0) != 0:
            summary.append(f"最大利益: {metrics.get('max_profit', 0):.2%}")
        if metrics.get('max_loss', 0) != 0:
            summary.append(f"最大損失: {metrics.get('max_loss', 0):.2%}")
        
        # Trade details
        buy_trades = [t for t in trades if t['action'] == 'BUY']
        sell_trades = [t for t in trades if t['action'] == 'SELL']
        
        if buy_trades:
            summary.append("\n【買いシグナル】")
            for trade in buy_trades:
                summary.append(f"  {trade['date']}: ¥{trade['price']:.2f} - {trade['reason']}")
        
        if sell_trades:
            summary.append("\n【売りシグナル】")
            for trade in sell_trades:
                profit_info = ""
                if 'profit_loss_percent' in trade:
                    profit_info = f" (損益: {trade['profit_loss_percent']:.2%})"
                summary.append(f"  {trade['date']}: ¥{trade['price']:.2f} - {trade['reason']}{profit_info}")
        
        return "\n".join(summary)
    
    def visualize_all_stocks(self, portfolio_file: str = "portfolio_practice.csv"):
        """全銘柄のチャートを作成"""
        
        print(f"=== 全銘柄チャート作成開始 ===")
        print(f"対象ポートフォリオ: {portfolio_file}")
        
        # Load portfolio
        stocks = self.load_portfolio_stocks(portfolio_file)
        if not stocks:
            print("ポートフォリオが読み込めませんでした")
            return
        
        # Process each stock
        summary_report = []
        successful_charts = 0
        
        for i, stock_info in enumerate(stocks, 1):
            try:
                print(f"\n[{i}/{len(stocks)}] 処理中: {stock_info['name']} ({stock_info['code']})")
                
                # Fetch data
                df = self.fetch_stock_data(stock_info['code'])
                if df is None:
                    continue
                
                # Analyze with trading rules
                trades = self.trading_rules.analyze_with_improved_rules(df)
                metrics = self.trading_rules.calculate_performance_metrics(trades)
                
                # Create chart
                fig = self.create_chart_with_signals(stock_info, df, trades)
                
                # Save chart
                chart_filename = f"{stock_info['code'].replace('.', '_')}_{stock_info['name']}.png"
                chart_path = os.path.join(self.output_dir, chart_filename)
                fig.savefig(chart_path, dpi=150, bbox_inches='tight')
                plt.close(fig)
                
                print(f"  チャート保存: {chart_path}")
                
                # Generate summary
                summary = self.generate_trading_summary(stock_info, trades, metrics)
                summary_report.append(summary)
                
                successful_charts += 1
                
            except Exception as e:
                print(f"  エラー: {stock_info['code']} - {e}")
                continue
        
        # Save summary report
        self.save_summary_report(summary_report, portfolio_file)
        
        print(f"\n=== 処理完了 ===")
        print(f"成功: {successful_charts}/{len(stocks)} 銘柄")
        print(f"チャート保存先: {os.path.abspath(self.output_dir)}")
    
    def save_summary_report(self, summaries: List[str], portfolio_file: str):
        """サマリーレポートを保存"""
        try:
            report_filename = f"trading_summary_{portfolio_file.replace('.csv', '')}.txt"
            report_path = os.path.join(self.output_dir, report_filename)
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(f"=== 全銘柄売買タイミング分析レポート ===\n")
                f.write(f"作成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"対象ポートフォリオ: {portfolio_file}\n")
                f.write("="*60 + "\n")
                
                for summary in summaries:
                    f.write(summary + "\n\n")
            
            print(f"サマリーレポート保存: {report_path}")
            
        except Exception as e:
            print(f"レポート保存エラー: {e}")

def main():
    """メイン関数"""
    
    # Available portfolios
    portfolios = [
        "codes.csv",  # 実際の運用用
        "portfolio_practice.csv",  # 練習用
        "portfolio_beginner.csv", 
        "portfolio_diversified.csv",
        "portfolio_growth.csv",
        "portfolio_stable.csv"
    ]
    
    print("=== 株価チャート可視化ツール ===")
    print("利用可能なポートフォリオ:")
    for i, portfolio in enumerate(portfolios, 1):
        if portfolio == "codes.csv":
            print(f"{i}. {portfolio} (実際の運用用)")
        else:
            print(f"{i}. {portfolio} (練習用)")
    
    # User selection
    try:
        choice = input(f"\nポートフォリオを選択してください (1-{len(portfolios)}, デフォルト: 1): ").strip()
        if not choice:
            choice = "1"
        
        portfolio_index = int(choice) - 1
        if portfolio_index < 0 or portfolio_index >= len(portfolios):
            print("無効な選択です。デフォルトを使用します。")
            portfolio_index = 0
        
        selected_portfolio = portfolios[portfolio_index]
        
        # Period selection
        period = input("期間を選択してください (1mo, 3mo, 6mo, 1y, デフォルト: 3mo): ").strip()
        if not period:
            period = "3mo"
        
        # Create visualizer and run
        visualizer = StockChartVisualizer(period=period)
        visualizer.visualize_all_stocks(selected_portfolio)
        
    except KeyboardInterrupt:
        print("\n処理を中断しました。")
    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
