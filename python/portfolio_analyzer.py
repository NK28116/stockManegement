"""
ポートフォリオ分析モジュール
リスク・リターン分析と分散投資の評価
"""

import yfinance as yf
import pandas as pd
import numpy as np
import sqlite3
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import matplotlib.pyplot as plt
# import seaborn as sns

# 現在のディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import config

# Ensure logs directory exists
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/portfolio_analyzer.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PortfolioAnalyzer:
    """ポートフォリオ分析クラス"""
    
    def __init__(self):
        self.db_config = config.get_database_config()
        self.risk_free_rate = 0.001  # 無リスク金利（年率0.1%）
    
    def load_portfolio_from_file(self, file_path: str) -> Dict[str, Dict]:
        """
        外部ファイルからポートフォリオ情報を読み込み
    
        Args:
            file_path: CSVファイルのパス
        
        Returns:
            Dict: ポートフォリオ情報
        """
        try:
            print(f"ファイル読み込み開始: {file_path}")
            
            # ファイルの存在確認
            if not os.path.exists(file_path):
                print(f"ファイルが存在しません: {file_path}")
                return {}
            
            # ファイルサイズ確認
            file_size = os.path.getsize(file_path)
            print(f"ファイルサイズ: {file_size} bytes")
            
            # CSV読み込み
            df = pd.read_csv(file_path)
            print(f"CSV読み込み完了: {len(df)}行")
            print(f"列名: {list(df.columns)}")
            
            portfolio = {}
            
            for idx, row in df.iterrows():
                try:
                    code = row['code']
                    print(f"処理中: {code}")
                    
                    portfolio[code] = {
                        'name': row.get('name', code),
                        'quantity': int(row['quantity']),
                        'purchase_price': float(row['purchase_price']),
                        'purchase_date': row.get('purchase_date', ''),
                        'sector': row.get('sector', ''),
                        'weight': 0.0  # 後で計算
                    }
                    print(f"  {code} の処理完了")
                    
                except Exception as row_error:
                    print(f"行 {idx} の処理エラー: {row_error}")
                    print(f"行データ: {row.to_dict()}")
                    continue
            
            if not portfolio:
                print("ポートフォリオが空です")
                return {}
            
            # ウェイト計算
            total_value = sum(item['quantity'] * item['purchase_price'] for item in portfolio.values())
            print(f"総投資額: {total_value:,.0f}円")
            
            for item in portfolio.values():
                item['weight'] = (item['quantity'] * item['purchase_price']) / total_value
            
            print(f"ポートフォリオ読み込み完了: {len(portfolio)}銘柄")
            return portfolio
            
        except Exception as e:
            print(f"ポートフォリオ読み込みエラー: {e}")
            import traceback
            traceback.print_exc()
            return {}    
    def fetch_historical_data(self, codes: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """
        複数銘柄の履歴データを取得
        
        Args:
            codes: 証券コードのリスト
            start_date: 開始日 (YYYY-MM-DD)
            end_date: 終了日 (YYYY-MM-DD)
            
        Returns:
            Dict: 銘柄コードとデータフレームの辞書
        """
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
    
    def calculate_returns(self, data: Dict[str, pd.DataFrame]) -> Dict[str, pd.Series]:
        """各銘柄のリターンを計算"""
        returns = {}
        
        for code, df in data.items():
            if not df.empty:
                returns[code] = df['Close'].pct_change().dropna()
        
        return returns
    
    def calculate_portfolio_metrics(self, portfolio: Dict, returns: Dict[str, pd.Series]) -> Dict:
        """
        ポートフォリオの主要指標を計算
        
        Args:
            portfolio: ポートフォリオ情報
            returns: 各銘柄のリターン
            
        Returns:
            Dict: ポートフォリオ指標
        """
        try:
            # ポートフォリオリターン計算
            portfolio_returns = pd.Series(0.0, index=next(iter(returns.values())).index)
            
            for code, weight in {k: v['weight'] for k, v in portfolio.items()}.items():
                if code in returns:
                    portfolio_returns += weight * returns[code]
            
            # 基本統計量
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
    
    def calculate_correlation_matrix(self, returns: Dict[str, pd.Series]) -> pd.DataFrame:
        """相関行列を計算"""
        try:
            # 全てのリターンを同じ期間に揃える
            aligned_returns = pd.DataFrame(returns)
            correlation_matrix = aligned_returns.corr()
            return correlation_matrix
        except Exception as e:
            logger.error(f"相関行列計算エラー: {e}")
            return pd.DataFrame()
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """最大ドローダウンを計算"""
        cumulative = (returns + 1).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min()
    
    def generate_portfolio_report(self, portfolio: Dict, metrics: Dict, correlation_matrix: pd.DataFrame) -> str:
        """ポートフォリオ分析レポートを生成"""
        report = []
        report.append("=" * 60)
        report.append("ポートフォリオ分析レポート")
        report.append("=" * 60)
        report.append(f"分析日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"対象銘柄数: {len(portfolio)}")
        report.append("")
        
        # ポートフォリオ概要
        report.append("【ポートフォリオ概要】")
        total_value = sum(item['quantity'] * item['purchase_price'] for item in portfolio.values())
        report.append(f"総投資額: {total_value:,.0f}円")
        report.append("")
        
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
            report.append("")
        
        # ポートフォリオ指標
        report.append("【ポートフォリオ指標】")
        report.append(f"総リターン: {metrics.get('total_return', 0):.2%}")
        report.append(f"年率リターン: {metrics.get('annualized_return', 0):.2%}")
        report.append(f"ボラティリティ: {metrics.get('volatility', 0):.2%}")
        report.append(f"シャープレシオ: {metrics.get('sharpe_ratio', 0):.2f}")
        report.append(f"最大ドローダウン: {metrics.get('max_drawdown', 0):.2%}")
        report.append(f"VaR(95%): {metrics.get('var_95', 0):.2%}")
        report.append(f"VaR(99%): {metrics.get('var_99', 0):.2%}")
        report.append("")
        
        # 分散効果
        report.append("【分散効果】")
        if len(portfolio) > 1:
            avg_correlation = (correlation_matrix.sum().sum() - len(correlation_matrix)) / (len(correlation_matrix) ** 2 - len(correlation_matrix))
            report.append(f"平均相関係数: {avg_correlation:.3f}")
            
            if avg_correlation < 0.3:
                report.append("✅ 良好な分散効果")
            elif avg_correlation < 0.6:
                report.append("⚠️ 中程度の分散効果")
            else:
                report.append("❌ 分散効果が限定的")
        report.append("")
        
        # 推奨事項
        report.append("【推奨事項】")
        if metrics.get('sharpe_ratio', 0) < 1.0:
            report.append("• リスク調整後リターンの改善を検討")
        if metrics.get('max_drawdown', 0) < -0.15:
            report.append("• リスク管理の強化を検討")
        if len(portfolio) < 5:
            report.append("• 銘柄数の増加を検討")
        
        return "\n".join(report)
    
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

def analyze_portfolio_sample():
    """サンプルポートフォリオの分析（6-8月データ使用）"""
    analyzer = PortfolioAnalyzer()
    
    # 相対パスでファイルを指定（python/ディレクトリから実行する場合）
    portfolio_file = "../data/codes.csv"
    
    print(f"ポートフォリオファイル: {portfolio_file}")
    
    # 特定のCSVファイルを読み込み
    portfolio = analyzer.load_portfolio_from_file(portfolio_file)
    
    if not portfolio:
        print("ポートフォリオの読み込みに失敗しました")
        return
    
    # 6-8月のデータを取得
    start_date = "2024-06-01"
    end_date = "2024-08-31"
    
    print("データ取得中...")
    data = analyzer.fetch_historical_data(list(portfolio.keys()), start_date, end_date)
    
    if not data:
        print("データ取得に失敗しました")
        return
    
    print("分析中...")
    returns = analyzer.calculate_returns(data)
    metrics = analyzer.calculate_portfolio_metrics(portfolio, returns)
    
    # calculate_correlation_matrix が存在しない場合に備えてチェック
    if hasattr(analyzer, "calculate_correlation_matrix"):
        correlation_matrix = analyzer.calculate_correlation_matrix(returns)
    else:
        correlation_matrix = None
    
    print("レポート生成中...")
    report = analyzer.generate_portfolio_report(portfolio, metrics, correlation_matrix)
    
    # 結果表示
    print(report)
    
    # ファイル保存
    analyzer.save_analysis_result(report, "my_portfolio_analysis.txt")

def analyze_custom_portfolio(csv_file: str):
    """カスタムポートフォリオの分析"""
    analyzer = PortfolioAnalyzer()
    
    # CSVファイルを読み込み
    portfolio = analyzer.load_portfolio_from_file(csv_file)
    
    if not portfolio:
        print(f"ポートフォリオの読み込みに失敗しました: {csv_file}")
        return
    
    # 6-8月のデータを取得
    start_date = "2024-06-01"
    end_date = "2024-08-31"
    
    print(f"データ取得中... ({csv_file})")
    data = analyzer.fetch_historical_data(list(portfolio.keys()), start_date, end_date)
    
    if not data:
        print("データ取得に失敗しました")
        return
    
    print("分析中...")
    returns = analyzer.calculate_returns(data)
    metrics = analyzer.calculate_portfolio_metrics(portfolio, returns)
    correlation_matrix = analyzer.calculate_correlation_matrix(returns)
    
    print("レポート生成中...")
    report = analyzer.generate_portfolio_report(portfolio, metrics, correlation_matrix)
    
    # 結果表示
    print(report)
    
    # ファイル保存
    filename = f"analysis_{os.path.basename(csv_file).replace('.csv', '')}.txt"
    analyzer.save_analysis_result(report, filename)

if __name__ == "__main__":
    # デフォルトのサンプル分析
    analyze_portfolio_sample()
    
    # 他のポートフォリオも分析したい場合
    # analyze_custom_portfolio('../data/portfolio_growth.csv')
    # analyze_custom_portfolio('../data/portfolio_diversified.csv')
