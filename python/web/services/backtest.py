# python/web/services/backtest.py
import yfinance as yf
from datetime import datetime, timedelta
from python.trading.trading_rules import ImprovedTradingRules

def evaluate_rule_risk(rules: TradingRules) -> list[str]:
    flags = []

    if rules.risk_management.stop_loss_percent > 0.2:
        flags.append("Stop loss is too wide (>20%)")

    if rules.risk_management.risk_per_trade >= 1.0:
        flags.append("Risk per trade is 100% (account blow risk)")

    if rules.exit_rules.take_profit.enabled is False:
        flags.append("Take profit is disabled")

    return flags



def run_backtest(rules, days: int = 180):
    ticker = "7203.T"  # ← 後で複数銘柄化
    start = datetime.now() - timedelta(days=days)

    df = yf.Ticker(ticker).history(start=start)

    engine = ImprovedTradingRules(rules)
    trades = engine.analyze_with_improved_rules(df)
    metrics = engine.calculate_performance_metrics(trades)

    return {
        "symbol": ticker,
        "period_days": days,
        "metrics": metrics,
        "trade_count": len(trades),
        "risk_flags": evaluate_risk(metrics),
    }
