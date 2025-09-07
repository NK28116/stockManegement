# python/analysis/portfolio_analyzer.py
"""
ポートフォリオ分析モジュール
リスク・リターン分析、テクニカル指標、分散投資評価
"""

import yfinance as yf
import pandas as pd
import numpy as np
import sqlite3
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List
from visualization.plot_indicators import plot_macd_bollinger


import matplotlib.pyplot as plt
# import seaborn as sns

# --- utils パス追加 ---
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from config import config
from utils.indicator import calculate_macd, calculate_bollinger_bands

# --- ログ設定 ---
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'portfolio_analyzer.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PortfolioAnalyzer:
    """ポートフォリオ分析クラス"""
    
    def __init__(self):
        self.db_config = config.get_db_config()
        self.risk_free_rate = 0.001  # 無リスク金利（年率0.1%）
    
    # --- ポートフォリオ読み込み ---
    def load_portfolio_from_file(self, file_path: str) -> Dict[str, Dict]:
        """CSVファイルからポートフォリオ情報を読み込み"""
        try:
            if not os.path.exists(file_path):
                logger.error(f"ファイルが存在しません: {file_path}")
                return {}
            df = pd.read_csv(file_path)
            portfolio = {}
            for idx, row in df.iterrows():
                try:
                    code = row['code']
                    portfolio[code] = {
                        'name': row.get('name', code),
                        'quantity': int(row['quantity']),
                        'purchase_price': float(row['purchase_price']),
                        'purchase_date': row.get('purchase_date', ''),
                        'sector': row.get('sector', ''),
                        'weight': 0.0
                    }
                except Exception as e:
                    logger.warning(f"行 {idx} の処理エラー: {e}")
                    continue
            if not portfolio:
                return {}
            total_value = sum(item['quantity'] * item['purchase_price'] for item in portfolio.values())
            for item in portfolio.values():
                item['weight'] = (item['quantity'] * item['purchase_price']) / total_value
            return portfolio
        except Exception as e:
            logger.error(f"ポートフォリオ読み込みエラー: {e}")
            return {}
    
    # --- 株価データ取得 ---
    def fetch_historical_data(self, codes: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """複数銘柄の履歴データを取得"""
        data = {}
        for code in codes:
            try:
                ticker = yf.Ticker(code)
                df = ticker.history(start=start_date, end=end_date)
                if not df.empty:
                    data[code] = df
                    logger.info(f"データ取得完了: {code} - {len(df)}件")
                else:
                    logger.warning(f"データが取得できません: {code}")
            except Exception as e:
                logger.error(f"データ取得エラー: {code} - {e}")
        return data
    
    # --- リターン計算 ---
    def calculate_returns(self, data: Dict[str, pd.DataFrame]) -> Dict[str, pd.Series]:
        """各銘柄のリターンを計算"""
        returns = {}
        for code, df in data.items():
            if not df.empty:
                returns[code] = df['Close'].pct_change().dropna()
        return returns
    
    # --- ポートフォリオ指標 ---
    def calculate_portfolio_metrics(self, portfolio: Dict, returns: Dict[str, pd.Series]) -> Dict:
        """ポートフォリオ指標計算"""
        if not returns:
            return {}
        try:
            first_series = next(iter(returns.values()))
            portfolio_returns = pd.Series(0.0, index=first_series.index)
            for code, weight in {k: v['weight'] for k, v in portfolio.items()}.items():
                if code in returns:
                    portfolio_returns += weight * returns[code]
            metrics = {
                'total_return': (portfolio_returns + 1).prod() - 1,
                'annualized_return': (portfolio_returns + 1).prod() ** (252 / len(portfolio_returns)) - 1,
                'volatility': portfolio_returns.std() * np.sqrt(252),
                'sharpe_ratio': (portfolio_returns.mean() * 252 - self.risk_free_rate) / (portfolio_returns.std() * np.sqrt(252)),
                'max_drawdown': self._calculate_max_drawdown(portfolio_returns),
                'var_95': np.percentile(portfolio_returns, 5),
                'var_99': np.percentile(portfolio_returns, 1),
            }
            # 銘柄別分析
            individual_metrics = {}
            for code in portfolio.keys():
                if code in returns:
                    ret = returns[code]
                    individual_metrics[code] = {
                        'return': (ret + 1).prod() - 1,
                        'volatility': ret.std() * np.sqrt(252),
                        'sharpe': (ret.mean() * 252 - self.risk_free_rate) / (ret.std() * np.sqrt(252)),
                        'max_drawdown': self._calculate_max_drawdown(ret)
                    }
            metrics['individual_metrics'] = individual_metrics
            return metrics
        except Exception as e:
            logger.error(f"ポートフォリオ指標計算エラー: {e}")
            return {}
    
    # --- 最大ドローダウン ---
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """最大ドローダウンを計算"""
        cum_returns = (1 + returns).cumprod()
        peak = cum_returns.cummax()
        drawdown = (cum_returns - peak) / peak
        return drawdown.min()
    
    # --- 相関行列 ---
    def calculate_correlation_matrix(self, returns: Dict[str, pd.Series]) -> pd.DataFrame:
        """相関行列を計算"""
        try:
            aligned_returns = pd.DataFrame(returns)
            return aligned_returns.corr()
        except Exception as e:
            logger.error(f"相関行列計算エラー: {e}")
            return pd.DataFrame()
    
    # --- テクニカル指標計算 ---
    def calculate_technical_indicators(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, pd.DataFrame]]:
        """MACDとボリンジャーバンドを計算"""
        indicators = {}
        for code, df in data.items():
            if df.empty or 'Close' not in df.columns:
                continue
            close = df['Close']
            macd_df = calculate_macd(close)
            bb_df = calculate_bollinger_bands(close)
            indicators[code] = {
                'MACD': macd_df,
                'Bollinger': bb_df
            }
        return indicators
    
    # --- レポート生成 ---
    def generate_portfolio_report(self, portfolio: Dict, metrics: Dict, correlation_matrix: pd.DataFrame, indicators: Dict = None) -> str:
        """ポートフォリオ分析レポート生成"""
        report = []
        report.append("=" * 60)
        report.append("ポートフォリオ分析レポート")
        report.append("=" * 60)
        report.append(f"分析日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"対象銘柄数: {len(portfolio)}\n")

        # 銘柄別詳細
        report.append("【銘柄別詳細】")
        for code, item in portfolio.items():
            report.append(f"{code} ({item['name']})")
            report.append(f"  数量: {item['quantity']:,}株")
            report.append(f"  購入価格: {item['purchase_price']:,.0f}円")
            report.append(f"  投資額: {item['quantity'] * item['purchase_price']:,.0f}円")
            report.append(f"  ウェイト: {item['weight']:.2%}")
            if code in metrics.get('individual_metrics', {}):
                ind_metrics = metrics['individual_metrics'][code]
                report.append(f"  リターン: {ind_metrics['return']:.2%}")
                report.append(f"  ボラティリティ: {ind_metrics['volatility']:.2%}")
                report.append(f"  シャープレシオ: {ind_metrics['sharpe']:.2f}")
            # テクニカル指標
            if indicators and code in indicators:
                macd = indicators[code]['MACD'].iloc[-1].to_dict()
                bb = indicators[code]['Bollinger'].iloc[-1].to_dict()
                report.append(f"  MACD: {macd}")
                report.append(f"  Bollinger: {bb}")
            report.append("")

        # ポートフォリオ指標
        report.append("【ポートフォリオ指標】")
        report.append(f"総リターン: {metrics.get('total_return', 0):.2%}")
        report.append(f"年率リターン: {metrics.get('annualized_return', 0):.2%}")
        report.append(f"ボラティリティ: {metrics.get('volatility', 0):.2%}")
        report.append(f"シャープレシオ: {metrics.get('sharpe_ratio', 0):.2f}")
        report.append(f"最大ドローダウン: {metrics.get('max_drawdown', 0):.2%}")
        report.append(f"VaR(95%): {metrics.get('var_95', 0):.2%}")
        report.append(f"VaR(99%): {metrics.get('var_99', 0):.2%}\n")

        # 分散効果
        report.append("【分散効果】")
        if len(portfolio) > 1 and correlation_matrix is not None and len(correlation_matrix) > 1:
            denom = len(correlation_matrix) ** 2 - len(correlation_matrix)
            if denom != 0:
                avg_correlation = (correlation_matrix.sum().sum() - len(correlation_matrix)) / denom
                report.append(f"平均相関係数: {avg_correlation:.3f}")
                if avg_correlation < 0.3:
                    report.append("✅ 良好な分散効果")
                elif avg_correlation < 0.6:
                    report.append("⚠️ 中程度の分散効果")
                else:
                    report.append("❌ 分散効果が限定的")
        else:
            report.append("平均相関係数: N/A\n")
        return "\n".join(report)
    
    # --- 結果保存 ---
    def save_analysis_result(self, report: str, filename: str = None) -> bool:
        """分析結果を保存"""
        try:
            if filename is None:
                filename = f"portfolio_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            filepath = os.path.join("../data", filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"分析結果を保存: {filepath}")
            return True
        except Exception as e:
            logger.error(f"結果保存エラー: {e}")
            return False

def analyze_portfolio():
    analyzer = PortfolioAnalyzer()
    portfolio_file = "../data/my_stock.csv"
    
    # 1. ポートフォリオ読み込み
    portfolio = analyzer.load_portfolio_from_file(portfolio_file)
    if not portfolio:
        logger.error("ポートフォリオが空です。処理を中止します。")
        return

    # 2. データ取得期間設定
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')  # 過去1年

    # 3. 株価データ取得
    codes = list(portfolio.keys())
    price_data = analyzer.fetch_historical_data(codes, start_date, end_date)
    if not price_data:
        logger.error("株価データが取得できませんでした。")
        return

    # 4. リターン計算
    returns = analyzer.calculate_returns(price_data)

    # 5. ポートフォリオ指標計算
    metrics = analyzer.calculate_portfolio_metrics(portfolio, returns)

    # 6. 相関行列計算
    correlation_matrix = analyzer.calculate_correlation_matrix(returns)

    # 7. テクニカル指標計算（MACD & Bollinger）
    indicators = analyzer.calculate_technical_indicators(price_data)

    # 8. レポート生成
    report = analyzer.generate_portfolio_report(portfolio, metrics, correlation_matrix, indicators)

    # 9. レポート保存
    analyzer.save_analysis_result(report)

    # 10. ログ出力
    logger.info("ポートフォリオ分析が完了しました。")
    print("テクニカル指標グラフを生成中...")
    plot_macd_bollinger(data, indicators)

if __name__ == "__main__":
    analyze_portfolio()