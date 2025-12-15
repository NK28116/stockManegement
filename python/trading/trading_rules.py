from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from python.web.schemas import TradingRules
from python.utils.rules_loader import get_active_rules

__all__ = ["ImprovedTradingRules", "generate_trading_report"]


class ImprovedTradingRules:
    """売買ルールクラス"""

    def __init__(self, rules: TradingRules):
        """
        初期化

        Args:
            rules (TradingRules): 売買ルール設定
        """
        if not rules.is_active:
            raise ValueError("TradingRules is inactive")
        self.rules = rules

    def match_price_pattern(self, signals: List[str], i: int, pattern: str) -> bool:
        """
        価格パターンのマッチング判定

        Args:
            signals: シグナルリスト
            i: 現在のインデックス
            pattern: 判定するパターン (例: "++")
        """
        if not pattern:
            return False

        current_pattern = signals[i - 1] + signals[i]
        return current_pattern == pattern

    def should_enter(self, signals: List[str], i: int) -> bool:
        """
        エントリー条件判定

        Args:
            signals: シグナルリスト
            i: 現在のインデックス

        Returns:
            bool: エントリーすべきかどうか
        """
        # Price Momentum Rule
        momentum_rule = self.rules.entry_rules.price_momentum
        if momentum_rule.enabled:
            if self.match_price_pattern(signals, i, momentum_rule.pattern):
                return True

        # 拡張性のために他のエントリー条件もここに追記可能

        return False

    def should_exit(self, current_price: float, position: Dict, signals: List[str], i: int) -> Optional[str]:
        """
        イグジット条件判定

        Args:
            current_price: 現在価格
            position: 現在のポジション情報
            signals: シグナルリスト
            i: 現在のインデックス

        Returns:
            Optional[str]: 売却理由 (売却不要な場合は None)
        """
        exit_rules = self.rules.exit_rules

        # 1. Stop Loss
        if exit_rules.stop_loss.enabled:
            # Use rules-based stop loss percentage if dynamic calculation is desired,
            # but position usually has fixed prices calculated at entry.
            # Here checking against position['stop_loss_price'] which was calculated based on rules at entry.
            if current_price <= position["stop_loss_price"]:
                return f"ストップロス（-{self.rules.risk_management.stop_loss_percent:.1%}）"

        # 2. Take Profit
        if exit_rules.take_profit.enabled:
            if current_price >= position["take_profit_price"]:
                return f"利確（+{self.rules.risk_management.take_profit_percent:.1%}）"

        # 3. Dead Cross (Signals)
        if exit_rules.dead_cross_exit.enabled:
            pattern = exit_rules.dead_cross_exit.pattern
            if pattern and self.match_price_pattern(signals, i, pattern):
                return f"デッドクロス（{pattern}）売却"

        return None

    def analyze_with_improved_rules(self, df: pd.DataFrame) -> List[Dict]:
        """
        売買ルールで分析

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
            change = "+" if closes[i] > closes[i - 1] else "-"
            signals.append(change)

        trades = []
        position = None  # 現在のポジション情報

        for i in range(1, len(signals)):
            pattern = signals[i - 1] + signals[i]
            date = df.index[i].strftime("%Y-%m-%d")
            price = closes[i]

            # ポジションがない場合のエントリー判定
            if position is None:
                if self.should_enter(signals, i):
                    position = {
                        "entry_date": date,
                        "entry_price": price,
                        "entry_pattern": pattern,
                        "highest_price": price,  # 最高値追跡
                        "stop_loss_price": price * (1 - self.rules.risk_management.stop_loss_percent),
                        "take_profit_price": price * (1 + self.rules.risk_management.take_profit_percent),
                    }
                    trades.append(
                        {
                            "date": date,
                            "price": price,
                            "action": "BUY",
                            "pattern": pattern,
                            "reason": f"パターン（{pattern}）エントリー",
                        }
                    )

            # ポジションがある場合の管理
            else:
                # 最高値更新
                if price > position["highest_price"]:
                    position["highest_price"] = price
                    # トレーリングストップ更新
                    new_stop = price * (1 - self.rules.risk_management.trailing_stop_percent)
                    if new_stop > position["stop_loss_price"]:
                        position["stop_loss_price"] = new_stop

                # 売却判定
                exit_reason = self.should_exit(price, position, signals, i)
                if exit_reason:
                    trades.append(
                        {
                            "date": date,
                            "price": price,
                            "action": "SELL",
                            "pattern": pattern,
                            "reason": exit_reason,
                            "entry_price": position["entry_price"],
                            "profit_loss": price - position["entry_price"],
                            "profit_loss_percent": (price - position["entry_price"]) / position["entry_price"],
                        }
                    )
                    position = None
                else:
                    # 継続保持
                    trades.append(
                        {
                            "date": date,
                            "price": price,
                            "action": "HOLD",
                            "pattern": pattern,
                            "reason": f'継続保持（ストップ値: {position["stop_loss_price"]:.2f}円）',
                        }
                    )

        return trades

    def calculate_performance_metrics(self, trades: List[Dict]) -> Dict:
        """取引パフォーマンスを計算"""
        if not trades:
            return {}

        buy_trades = [t for t in trades if t["action"] == "BUY"]
        sell_trades = [t for t in trades if t["action"] == "SELL"]

        if len(sell_trades) == 0:
            return {"total_trades": len(buy_trades), "completed_trades": 0}

        # 損益計算
        profits = [t["profit_loss_percent"] for t in sell_trades if "profit_loss_percent" in t]

        metrics = {
            "total_trades": len(buy_trades),
            "completed_trades": len(sell_trades),
            "win_rate": (len([p for p in profits if p > 0]) / len(profits) if profits else 0),
            "average_profit": np.mean(profits) if profits else 0,
            "total_return": sum(profits) if profits else 0,
            "max_profit": max(profits) if profits else 0,
            "max_loss": min(profits) if profits else 0,
            "profit_factor": (
                sum([p for p in profits if p > 0]) / abs(sum([p for p in profits if p < 0]))
                if profits and any(p < 0 for p in profits)
                else float("inf")
            ),
        }

        return metrics


def generate_trading_report(comparison: Dict, is_test_mode: bool = False) -> str:
    """取引ルール比較レポートを生成し、ファイルに保存する"""
    report_content = []
    report_content.append("# -*- coding: utf-8 -*-\n")  # 文字コード宣言を追加
    report_content.append("=" * 60)
    report_content.append("売買ルール見直しレポート")
    report_content.append("=" * 60)
    report_content.append(f"分析日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_content.append("")

    # ルール
    report_content.append("ルール")
    new_metrics = comparison["new_rules"]["metrics"]
    report_content.append(f"総取引数: {new_metrics.get('total_trades', 0)}")
    report_content.append(f"完了取引数: {new_metrics.get('completed_trades', 0)}")
    report_content.append(f"勝率: {new_metrics.get('win_rate', 0):.2%}")
    report_content.append(f"平均損益: {new_metrics.get('average_profit', 0):.2%}")
    report_content.append(f"総リターン: {new_metrics.get('total_return', 0):.2%}")
    report_content.append(f"最大利益: {new_metrics.get('max_profit', 0):.2%}")
    report_content.append(f"最大損失: {new_metrics.get('max_loss', 0):.2%}")
    report_content.append(f"プロフィットファクター: {new_metrics.get('profit_factor', 0):.2f}")
    report_content.append("")

    # 推奨事項
    report_content.append("【推奨事項】")
    if new_metrics.get("win_rate", 0) < 0.4:
        report_content.append("• エントリー条件の見直しを検討")
    if new_metrics.get("max_loss", 0) < -0.1:
        report_content.append("• ストップロス幅の調整を検討")
    if new_metrics.get("profit_factor", 0) < 1.5:
        report_content.append("• 利確・損切りのバランス調整を検討")

    report_str = "\n".join(report_content)

    if not is_test_mode:
        # Resolve root_dir dynamically
        root_dir = Path(__file__).resolve().parent.parent.parent
        report_dir = root_dir / "data" / "report" / "monthly" / "trading_rules"
        os.makedirs(report_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"trading_rules_{timestamp}.txt"
        report_path = report_dir / report_filename

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_str)
        print(f"トレーディングルール見直しレポートを保存しました: {report_path}")
    else:
        print("テストモードのため、トレーディングルール見直しレポートの保存はスキップします。")

    return report_str


if __name__ == "__main__":
    # サンプルデータでテスト
    import yfinance as yf
    import os

    ticker = "7203.T"
    df = yf.Ticker(ticker).history(period="3mo")

    # Load active rules using the loader
    active_rules = get_active_rules()
    print(f"Using rules version: {active_rules.meta.version}")

    rules = ImprovedTradingRules(rules=active_rules)
    trades = rules.analyze_with_improved_rules(df)
    metrics = rules.calculate_performance_metrics(trades)

    comparison = {"new_rules": {"metrics": metrics}}

    report = generate_trading_report(comparison, is_test_mode=False)
