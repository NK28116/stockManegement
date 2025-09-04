"""
改善された売買判断ルール
リスク管理と利益確定を重視
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime

class ImprovedTradingRules:
    """改善された売買ルールクラス"""
    
    def __init__(self, 
                stop_loss_percent: float = 0.05,  # 5%ストップロス
                take_profit_percent: float = 0.10,  # 10%利確
                trailing_stop_percent: float = 0.03):  # 3%トレーリングストップ
        self.stop_loss_percent = stop_loss_percent
        self.take_profit_percent = take_profit_percent
        self.trailing_stop_percent = trailing_stop_percent
    
    def analyze_with_improved_rules(self, df: pd.DataFrame) -> List[Dict]:
        """
        改善されたルールで分析
        
        Args:
            df: 株価データ
            
        Returns:
            List[Dict]: 取引履歴
        """
        if df is None or df.empty:
            return []
        
        closes = df["Close"].tolist()
        signals = []
        
        # 価格変動シグナル生成
        for i in range(1, len(closes)):
            change = "+" if closes[i] > closes[i-1] else "-"
            signals.append(change)
        
        trades = []
        position = None  # 現在のポジション情報
        
        for i in range(1, len(signals)):
            pattern = signals[i-1] + signals[i]
            date = df.index[i].strftime("%Y-%m-%d")
            price = closes[i]
            
            # ポジションがない場合のエントリー判定
            if position is None:
                if pattern == "++":
                    position = {
                        'entry_date': date,
                        'entry_price': price,
                        'entry_pattern': pattern,
                        'highest_price': price,  # 最高値追跡
                        'stop_loss_price': price * (1 - self.stop_loss_percent),
                        'take_profit_price': price * (1 + self.take_profit_percent)
                    }
                    trades.append({
                        'date': date,
                        'price': price,
                        'action': 'BUY',
                        'pattern': pattern,
                        'reason': 'ゴールデンクロス（++）エントリー'
                    })
            
            # ポジションがある場合の管理
            else:
                # 最高値更新
                if price > position['highest_price']:
                    position['highest_price'] = price
                    # トレーリングストップ更新
                    new_stop = price * (1 - self.trailing_stop_percent)
                    if new_stop > position['stop_loss_price']:
                        position['stop_loss_price'] = new_stop
                
                # ストップロス判定
                if price <= position['stop_loss_price']:
                    trades.append({
                        'date': date,
                        'price': price,
                        'action': 'SELL',
                        'pattern': pattern,
                        'reason': f'ストップロス（-{self.stop_loss_percent:.1%}）',
                        'entry_price': position['entry_price'],
                        'profit_loss': price - position['entry_price'],
                        'profit_loss_percent': (price - position['entry_price']) / position['entry_price']
                    })
                    position = None
                
                # 利確判定
                elif price >= position['take_profit_price']:
                    trades.append({
                        'date': date,
                        'price': price,
                        'action': 'SELL',
                        'pattern': pattern,
                        'reason': f'利確（+{self.take_profit_percent:.1%}）',
                        'entry_price': position['entry_price'],
                        'profit_loss': price - position['entry_price'],
                        'profit_loss_percent': (price - position['entry_price']) / position['entry_price']
                    })
                    position = None
                
                # シグナルベースの売却判定（改善版）
                elif pattern == "--":
                    trades.append({
                        'date': date,
                        'price': price,
                        'action': 'SELL',
                        'pattern': pattern,
                        'reason': 'デッドクロス（--）売却',
                        'entry_price': position['entry_price'],
                        'profit_loss': price - position['entry_price'],
                        'profit_loss_percent': (price - position['entry_price']) / position['entry_price']
                    })
                    position = None
                
                # 継続判定
                else:
                    trades.append({
                        'date': date,
                        'price': price,
                        'action': 'HOLD',
                        'pattern': pattern,
                        'reason': f'継続保持（ストップ値: {position["stop_loss_price"]:.2f}円）'
                    })
        
        return trades
    
    def calculate_performance_metrics(self, trades: List[Dict]) -> Dict:
        """取引パフォーマンスを計算"""
        if not trades:
            return {}
        
        buy_trades = [t for t in trades if t['action'] == 'BUY']
        sell_trades = [t for t in trades if t['action'] == 'SELL']
        
        if len(sell_trades) == 0:
            return {'total_trades': len(buy_trades), 'completed_trades': 0}
        
        # 損益計算
        profits = [t['profit_loss_percent'] for t in sell_trades if 'profit_loss_percent' in t]
        
        metrics = {
            'total_trades': len(buy_trades),
            'completed_trades': len(sell_trades),
            'win_rate': len([p for p in profits if p > 0]) / len(profits) if profits else 0,
            'average_profit': np.mean(profits) if profits else 0,
            'total_return': sum(profits) if profits else 0,
            'max_profit': max(profits) if profits else 0,
            'max_loss': min(profits) if profits else 0,
            'profit_factor': sum([p for p in profits if p > 0]) / abs(sum([p for p in profits if p < 0])) if profits and any(p < 0 for p in profits) else float('inf')
        }
        
        return metrics


def generate_trading_report(comparison: Dict) -> str:
    """取引ルール比較レポートを生成"""
    report = []
    report.append("=" * 60)
    report.append("売買ルール比較レポート")
    report.append("=" * 60)
    report.append(f"分析日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    
    # 新ルール
    report.append("【新ルール（改善版）】")
    new_metrics = comparison['new_rules']['metrics']
    report.append(f"総取引数: {new_metrics.get('total_trades', 0)}")
    report.append(f"完了取引数: {new_metrics.get('completed_trades', 0)}")
    report.append(f"勝率: {new_metrics.get('win_rate', 0):.2%}")
    report.append(f"平均損益: {new_metrics.get('average_profit', 0):.2%}")
    report.append(f"総リターン: {new_metrics.get('total_return', 0):.2%}")
    report.append(f"最大利益: {new_metrics.get('max_profit', 0):.2%}")
    report.append(f"最大損失: {new_metrics.get('max_loss', 0):.2%}")
    report.append(f"プロフィットファクター: {new_metrics.get('profit_factor', 0):.2f}")
    report.append("")
    
    # 改善点
    report.append("【改善点】")
    report.append("✅ ストップロス機能追加（5%損失で自動売却）")
    report.append("✅ 利確機能追加（10%利益で自動売却）")
    report.append("✅ トレーリングストップ（3%で利益保護）")
    report.append("✅ リスク管理の強化")
    report.append("")
    
    # 推奨事項
    report.append("【推奨事項】")
    if new_metrics.get('win_rate', 0) < 0.4:
        report.append("• エントリー条件の見直しを検討")
    if new_metrics.get('max_loss', 0) < -0.1:
        report.append("• ストップロス幅の調整を検討")
    if new_metrics.get('profit_factor', 0) < 1.5:
        report.append("• 利確・損切りのバランス調整を検討")
    
    return "\n".join(report)

if __name__ == "__main__":
    # サンプルデータでテスト
    import yfinance as yf
    
    ticker = "7203.T"
    df = yf.Ticker(ticker).history(period="3mo")
    

    rules = ImprovedTradingRules()
    trades = rules.analyze_with_improved_rules(df)
    metrics = rules.calculate_performance_metrics(trades)
    
    comparison = {
        'new_rules': {
            'metrics': metrics
        }
    }
    
    report = generate_trading_report(comparison)
    print(report)
