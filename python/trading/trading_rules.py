"""
売買判断ルール
リスク管理と利益確定を重視
"""

import os
from datetime import datetime  # datetime を追加
from typing import Dict, List

import numpy as np
import pandas as pd

from python.config import config

__all__ = ["ImprovedTradingRules", "generate_trading_report"]


class ImprovedTradingRules:
    """売買ルールクラス"""

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
                if pattern == "++":
                    position = {
                        "entry_date": date,
                        "entry_price": price,
                        "entry_pattern": pattern,
                        "highest_price": price,  # 最高値追跡
                        "stop_loss_price": price * (1 - config.stop_loss_percent),
                        "take_profit_price": price * (1 + config.take_profit_percent),
                    }
                    trades.append(
                        {
                            "date": date,
                            "price": price,
                            "action": "BUY",
                            "pattern": pattern,
                            "reason": "ゴールデンクロス（++）エントリー",
                        }
                    )

            # ポジションがある場合の管理
            else:
                # 最高値更新
                if price > position["highest_price"]:
                    position["highest_price"] = price
                    # トレーリングストップ更新
                    new_stop = price * (1 - config.trailing_stop_percent)
                    if new_stop > position["stop_loss_price"]:
                        position["stop_loss_price"] = new_stop

                # ストップロス判定
                if price <= position["stop_loss_price"]:
                    trades.append(
                        {
                            "date": date,
                            "price": price,
                            "action": "SELL",
                            "pattern": pattern,
                            "reason": f"ストップロス（-{config.stop_loss_percent:.1%}）",
                            "entry_price": position["entry_price"],
                            "profit_loss": price - position["entry_price"],
                            "profit_loss_percent": (price - position["entry_price"])
                            / position["entry_price"],
                        }
                    )
                    position = None

                # 利確判定
                elif price >= position["take_profit_price"]:
                    trades.append(
                        {
                            "date": date,
                            "price": price,
                            "action": "SELL",
                            "pattern": pattern,
                            "reason": f"利確（+{config.take_profit_percent:.1%}）",
                            "entry_price": position["entry_price"],
                            "profit_loss": price - position["entry_price"],
                            "profit_loss_percent": (price - position["entry_price"])
                            / position["entry_price"],
                        }
                    )
                    position = None

                # シグナルベースの売却判定（改善版）
                elif pattern == "--":
                    trades.append(
                        {
                            "date": date,
                            "price": price,
                            "action": "SELL",
                            "pattern": pattern,
                            "reason": "デッドクロス（--）売却",
                            "entry_price": position["entry_price"],
                            "profit_loss": price - position["entry_price"],
                            "profit_loss_percent": (price - position["entry_price"])
                            / position["entry_price"],
                        }
                    )
                    position = None

                # 継続判定
                else:
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
        profits = [
            t["profit_loss_percent"] for t in sell_trades if "profit_loss_percent" in t
        ]

        metrics = {
            "total_trades": len(buy_trades),
            "completed_trades": len(sell_trades),
            "win_rate": (
                len([p for p in profits if p > 0]) / len(profits) if profits else 0
            ),
            "average_profit": np.mean(profits) if profits else 0,
            "total_return": sum(profits) if profits else 0,
            "max_profit": max(profits) if profits else 0,
            "max_loss": min(profits) if profits else 0,
            "profit_factor": (
                sum([p for p in profits if p > 0])
                / abs(sum([p for p in profits if p < 0]))
                if profits and any(p < 0 for p in profits)
                else float("inf")  # "in" を "inf" に修正
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
    report_content.append(
        f"プロフィットファクター: {new_metrics.get('profit_factor', 0):.2f}"
    )
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
        report_dir = config.root_dir / "data" / "report" / "monthly" / "trading_rules"
        os.makedirs(report_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"trading_rules_{timestamp}.txt"
        report_path = report_dir / report_filename

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_str)
        print(f"トレーディングルール見直しレポートを保存しました: {report_path}")
    else:
        print(
            "テストモードのため、トレーディングルール見直しレポートの保存はスキップします。"
        )

    return report_str


if __name__ == "__main__":
    # サンプルデータでテスト
    import yfinance as yf

    ticker = "7203.T"
    df = yf.Ticker(ticker).history(period="3mo")

    rules = ImprovedTradingRules()
    trades = rules.analyze_with_improved_rules(df)
    metrics = rules.calculate_performance_metrics(trades)

    comparison = {"new_rules": {"metrics": metrics}}

    report = generate_trading_report(
        comparison, is_test_mode=False
    )  # テストモードを明示的に指定
