#!/usr/bin/env python3
"""
全銘柄の売買タイミング分析
CSVファイルから銘柄を読み込んで一括分析
"""

import pandas as pd
import yfinance as yf
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

# 現在のディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trading_rules import ImprovedTradingRules, generate_trading_report

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/every_stock_analysis.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EveryStockAnalyzer:
    """全銘柄分析クラス"""
    
    def __init__(self, csv_file: str):
        self.csv_file = csv_file
        self.codes = self.load_codes_from_csv()
        self.analyzer = ImprovedTradingRules()
        
    def load_codes_from_csv(self) -> List[str]:
        """CSVファイルから銘柄コードを読み込み"""
        try:
            # ログディレクトリ作成
            os.makedirs('logs', exist_ok=True)
            
            # CSVファイル読み込み
            df = pd.read_csv(self.csv_file)
            
            # 銘柄コードの列を特定
            code_column = None
            for col in df.columns:
                if 'code' in col.lower() or 'ticker' in col.lower():
                    code_column = col
                    break
            
            if code_column is None:
                # 最初の列を銘柄コードとして使用
                code_column = df.columns[0]
            
            codes = df[code_column].dropna().tolist()
            
            # ティッカー形式に変換（.Tがない場合は追加）
            formatted_codes = []
            for code in codes:
                if isinstance(code, str):
                    if not code.endswith('.T') and not code.endswith('.JP'):
                        code = code + '.T'
                    formatted_codes.append(code)
            
            logger.info(f"銘柄コード読み込み完了: {len(formatted_codes)}銘柄")
            return formatted_codes
            
        except Exception as e:
            logger.error(f"CSVファイル読み込みエラー: {e}")
            return []
    
    def analyze_single_stock(self, code: str, period: str = "3mo") -> Dict:
        """単一銘柄の分析"""
        try:
            logger.info(f"分析開始: {code}")
            
            # データ取得
            ticker = yf.Ticker(code)
            df = ticker.history(period=period)
            
            if df.empty:
                logger.warning(f"データが取得できません: {code}")
                return {
                    'code': code,
                    'status': 'error',
                    'message': 'データが取得できません'
                }
            
            # 売買ルール分析
            trades = self.analyzer.analyze_with_improved_rules(df)
            metrics = self.analyzer.calculate_performance_metrics(trades)
            
            # 結果をまとめる
            result = {
                'code': code,
                'status': 'success',
                'data': df,  # データフレームを追加
                'data_period': f"{df.index[0].strftime('%Y-%m-%d')} ～ {df.index[-1].strftime('%Y-%m-%d')}",
                'data_count': len(df),
                'trades': trades,
                'metrics': metrics,
                'current_price': df['Close'].iloc[-1] if not df.empty else None,
                'price_change': ((df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0]) if len(df) > 1 else 0
            }
            
            logger.info(f"分析完了: {code} - 取引件数: {len(trades)}")
            return result
            
        except Exception as e:
            logger.error(f"分析エラー: {code} - {e}")
            return {
                'code': code,
                'status': 'error',
                'message': str(e)
            }
    
    def analyze_all_stocks(self, period: str = "3mo") -> List[Dict]:
        """全銘柄の分析"""
        logger.info(f"全銘柄分析開始: {len(self.codes)}銘柄")
        
        results = []
        for i, code in enumerate(self.codes, 1):
            print(f"分析中... {i}/{len(self.codes)}: {code}")
            result = self.analyze_single_stock(code, period)
            results.append(result)
            
            # 進捗表示
            if i % 5 == 0 or i == len(self.codes):
                print(f"進捗: {i}/{len(self.codes)} 完了")
        
        logger.info(f"全銘柄分析完了: {len(results)}銘柄")
        return results
    
    def generate_summary_report(self, results: List[Dict]) -> str:
        """サマリーレポート生成"""
        successful_results = [r for r in results if r['status'] == 'success']
        error_results = [r for r in results if r['status'] == 'error']
        
        report = []
        report.append("=" * 80)
        report.append("全銘柄売買タイミング分析レポート")
        report.append("=" * 80)
        report.append(f"分析日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"対象銘柄数: {len(self.codes)}")
        report.append(f"分析成功: {len(successful_results)}銘柄")
        report.append(f"分析失敗: {len(error_results)}銘柄")
        report.append("")

        if error_results:
            report.append("【分析失敗銘柄】")
            for error in error_results:
                report.append(f"• {error['code']}: {error['message']}")
            report.append("")

        if successful_results:
            report.append("【前日の各銘柄ステータス】")
            # 前日（カレンダー上の1日前。データ側の直近営業日に補正）
            target = datetime.now() - timedelta(days=1)
            for r in successful_results:
                line = self._get_status_for_date(r, target)
                report.append(f"{r['code']}: {line}")
            report.append("")

        return "\n".join(report)
    
    def _get_status_for_date(self, result: Dict, target_date: datetime) -> str:
        """指定日のステータスを 'YYYY-MM-DD: STATUS - 理由 (ストップ: XXX円)' 形式で返す"""
        try:
            df = result.get('data')
            trades = result.get('trades', [])
            if df is None or df.empty:
                return f"{target_date.strftime('%Y-%m-%d')}: データなし"

            # タイムゾーン除去 + 指定日以前で最後の営業日を取得
            idx = df.index.tz_localize(None) if getattr(df.index, 'tz', None) else df.index
            mask = idx <= target_date.replace(tzinfo=None)
            if not mask.any():
                return f"{target_date.strftime('%Y-%m-%d')}: データなし"
            day = idx[mask][-1]
            day_str = day.strftime('%Y-%m-%d')

            # 取引履歴から当日(=day)の記録を優先、それが無ければ直近過去の記録
            day_trade = None
            last_trade = None
            for t in trades:
                if 'date' not in t:
                    continue
                try:
                    td = pd.to_datetime(t.get('date'))
                    if hasattr(td, 'tz_localize'):
                        td = td.tz_localize(None)
                    if td.date() == day.date():
                        day_trade = t
                    if td <= day:
                        if (last_trade is None) or (pd.to_datetime(last_trade.get('date')).tz_localize(None) < td):
                            last_trade = t
                except Exception:
                    continue

            if day_trade:
                status = day_trade.get('action', 'HOLD')
                reason = day_trade.get('reason', '継続保持')
                stop_price = self.calculate_daily_stop_price(df, day, day_trade)
            elif last_trade:
                status = last_trade.get('action', 'HOLD')
                reason = last_trade.get('reason', '継続保持')
                stop_price = self.calculate_daily_stop_price(df, day, last_trade)
            else:
                status = 'HOLD'
                reason = '継続保持'
                stop_price = self.calculate_daily_stop_price(df, day, None)

            stop_txt = f" (ストップ: {stop_price}円)" if stop_price is not None else ""
            return f"{day_str}: {status} - {reason}{stop_txt}"
        except Exception as e:
            logger.error(f"前日ステータス取得エラー: {e}")
            return f"{target_date.strftime('%Y-%m-%d')}: 取得エラー"
    
    def generate_detailed_report(self, results: List[Dict]) -> str:
            """詳細レポート生成（損益詳細観察形式）"""
            successful_results = [r for r in results if r['status'] == 'success']
    
            report = []
            report.append("=" * 80)
            report.append("全銘柄損益詳細観察レポート")
            report.append("=" * 80)
            report.append(f"分析日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report.append("")
    
            for result in successful_results:
                # 基本情報
                report.append(f"資産名: {result['code']}-{result.get('name', '')}")
        
                # 購入情報（codes.csvから取得）
                purchase_info = self.get_purchase_info(result['code'])
                if purchase_info:
                    purchase_date = purchase_info.get('purchase_date', 'N/A')
                    purchase_price = purchase_info.get('purchase_price', 0)
                    quantity = purchase_info.get('quantity', 0)
                    report.append(f"購入日: {purchase_date}")
                    report.append(f"購入額(所持数): ¥{purchase_price:,.0f}({quantity}株)")
                else:
                    report.append("購入情報: N/A")
        
                report.append("---")
        
                # 月次損益計算
                monthly_returns = self.calculate_monthly_returns(result)
                for month, return_value in monthly_returns.items():
                    report.append(f"{month}: {return_value:+.2%}")
        
                report.append("---")
        
                # 直近1ヶ月の値動き（取引履歴形式）
                report.append("直近1ヶ月の値動き")
                daily_status = self.get_daily_status(result['data'], result['trades'], days=30)
                if daily_status:
                    for date, status_info in daily_status.items():
                        # 1行にまとめて表示
                        line = f"{date}: {status_info['status']} - {status_info['reason']}"
                        if status_info.get('stop_price'):
                            line += f" (ストップ: {status_info['stop_price']}円)"
                        report.append(line)
                else:
                    report.append("直近1ヶ月のデータなし")
        
                report.append("---")
        
                # 売却額と損益
                current_value = result['current_price'] * purchase_info.get('quantity', 0) if purchase_info else 0
                purchase_value = purchase_info.get('purchase_price', 0) * purchase_info.get('quantity', 0) if purchase_info else 0
                profit_loss = current_value - purchase_value
                profit_loss_percent = (profit_loss / purchase_value * 100) if purchase_value > 0 else 0
        
                report.append(f"売却額: ¥{current_value:,.0f}")
                report.append(f"損益: ¥{profit_loss:+,.0f} ({profit_loss_percent:+.2%})")
        
                report.append("")
                report.append("=" * 80)
                report.append("")
    
            return "\n".join(report)
    
    def save_reports(self, results: List[Dict]) -> None:
        """レポートを保存"""
        try:
            # サマリーレポート
            summary_report = self.generate_summary_report(results)
            summary_file = f"../data/report/summary/summary_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            os.makedirs(os.path.dirname(summary_file), exist_ok=True)
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary_report)
            
            print(f"サマリーレポート保存: {summary_file}")
            
            # 詳細レポート
            detailed_report = self.generate_detailed_report(results)
            detailed_file = f"../data/report/detailed/detailed_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            os.makedirs(os.path.dirname(detailed_file), exist_ok=True)
            
            with open(detailed_file, 'w', encoding='utf-8') as f:
                f.write(detailed_report)
            
            print(f"詳細レポート保存: {detailed_file}")
            
        except Exception as e:
            logger.error(f"レポート保存エラー: {e}")

    def get_purchase_info(self, code: str) -> Dict:
        """codes.csvから購入情報を取得"""
        try:
            codes_file = "../data/codes.csv"
            if os.path.exists(codes_file):
                df = pd.read_csv(codes_file)
                stock_info = df[df['code'] == code]
                if not stock_info.empty:
                    return stock_info.iloc[0].to_dict()
        except Exception as e:
            logger.error(f"購入情報取得エラー: {e}")
        return {}
    
    def calculate_monthly_returns(self, result: Dict) -> Dict[str, float]:
        """月次リターンを計算"""
        try:
            df = result['data']
            if df.empty:
                return {}
            
            # タイムゾーン情報を除去して月次リターン計算
            df_copy = df.copy()
            df_copy.index = df_copy.index.tz_localize(None)
            df_copy['month'] = df_copy.index.to_period('M')
            
            monthly_returns = {}
            for month in df_copy['month'].unique():
                month_data = df_copy[df_copy['month'] == month]
                if len(month_data) > 1:
                    start_price = month_data.iloc[0]['Close']
                    end_price = month_data.iloc[-1]['Close']
                    monthly_return = (end_price - start_price) / start_price
                    month_str = month.strftime('%Y年%m月')
                    monthly_returns[month_str] = monthly_return
            
            return monthly_returns
        except Exception as e:
            logger.error(f"月次リターン計算エラー: {e}")
            return {}
    
    def get_daily_status(self, df: pd.DataFrame, trades: List[Dict], days: int = 30) -> Dict[str, Dict]:
        """直近N日間の毎日のステータスと判断を取得"""
        try:
            if df.empty:
                return {}
            
            # 直近N日間のデータを取得（タイムゾーンを考慮）
            cutoff_date = datetime.now().replace(tzinfo=None) - timedelta(days=days)
            recent_data = df[df.index.tz_localize(None) >= cutoff_date].copy()
            
            if recent_data.empty:
                return {}
            
            daily_status = {}
            recent_data = recent_data.sort_index()
            
            # 取引履歴から日付ごとのステータスを取得
            trade_by_date = {}
            for trade in trades:
                trade_date = pd.to_datetime(trade['date']).strftime('%Y-%m-%d')
                trade_by_date[trade_date] = trade
            
            # 毎日のステータスを生成
            for date in recent_data.index:
                # タイムゾーン情報を除去して日付文字列を作成
                date_str = date.tz_localize(None).strftime('%Y-%m-%d')
                
                if date_str in trade_by_date:
                    # 取引がある日
                    trade = trade_by_date[date_str]
                    status = trade['action']
                    reason = trade['reason']
                    
                    # その日のストップ値を取得
                    stop_price = self.calculate_daily_stop_price(df, date, trade)
                    
                    daily_status[date_str] = {
                        'status': status,
                        'reason': reason,
                        'stop_price': stop_price
                    }
                else:
                    # 取引がない日（HOLD状態）
                    # その日のストップ値を計算
                    stop_price = self.calculate_daily_stop_price(df, date, None)
                    
                    daily_status[date_str] = {
                        'status': 'HOLD',
                        'reason': '継続保持',
                        'stop_price': stop_price
                    }
            
            return daily_status
        except Exception as e:
            logger.error(f"日次ステータス取得エラー: {e}")
            return {}
    
    def calculate_daily_stop_price(self, df: pd.DataFrame, date: datetime, trade: Dict = None) -> float:
        """その日のストップ値を計算"""
        try:
            # その日のデータを取得（タイムゾーンを考慮）
            date_data = df[df.index.tz_localize(None) == date.tz_localize(None)]
            if date_data.empty:
                return None
            
            current_price = date_data.iloc[0]['Close']
            
            # ストップロス設定（購入価格の5%下）
            # 実際の設定に応じて調整が必要
            stop_loss_percent = 0.05  # 5%
            
            # 購入価格が不明な場合は現在価格の5%下を仮設定
            purchase_price = current_price
            if trade and 'purchase_price' in trade:
                purchase_price = trade['purchase_price']
            
            stop_price = purchase_price * (1 - stop_loss_percent)
            
            return round(stop_price, 2)
            
        except Exception as e:
            logger.error(f"ストップ値計算エラー: {e}")
            return None

# 追加: 前日ステータス取得ヘルパ

def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='全銘柄の売買タイミングを分析')
    parser.add_argument('csv_file', help='銘柄コードが含まれるCSVファイル')
    parser.add_argument('--period', default='3mo', help='分析期間 (例: 1mo, 3mo, 6mo)')
    parser.add_argument('--output', choices=['summary', 'detailed', 'both'], default='both', help='出力タイプ')
    
    args = parser.parse_args()
    
    # ファイル存在確認
    if not os.path.exists(args.csv_file):
        print(f"エラー: ファイルが見つかりません: {args.csv_file}")
        return
    
    print(f"分析開始: {args.csv_file}")
    print(f"分析期間: {args.period}")
    print("=" * 60)
    
    # 分析実行
    analyzer = EveryStockAnalyzer(args.csv_file)
    
    if not analyzer.codes:
        print("銘柄コードの読み込みに失敗しました")
        return
    
    # 全銘柄分析
    results = analyzer.analyze_all_stocks(args.period)
    
    # 結果表示
    if args.output in ['summary', 'both']:
        print("\n" + "=" * 60)
        print("サマリーレポート")
        print("=" * 60)
        summary_report = analyzer.generate_summary_report(results)
        print(summary_report)
    
    if args.output in ['detailed', 'both']:
        print("\n" + "=" * 60)
        print("詳細レポート")
        print("=" * 60)
        print("詳細レポートはファイルに保存されました")
    
    # レポート保存
    analyzer.save_reports(results)
    
    print(f"\n分析完了: {len(analyzer.codes)}銘柄")

if __name__ == "__main__":
    main()
