# Trading Rules UI Integration Status

## Overview
Status tracking for the integration of the Web UI configuration (`rules.json`) with the core trading logic (`trading_rules.py`).

## Changes
- [x] **Web UI**: Implemented `index.html` with parameter editing and saving.
- [x] **Schema**: Defined `TradingRules` pydantic schema in `python/web/schemas.py`.
- [x] **Store**: Implemented `RuleStore` in `python/web/services/rule_store.py` to persist settings to `data/config/trading_rules.json`.
- [x] **Logic**: Refactoring `ImprovedTradingRules` in `python/trading/trading_rules.py` to accept dynamic configuration.
- [x] **Consumers**: Updating `EveryStockAnalyzer` and `StockChartVisualizer` to inject stored rules.

## Verification Result
- Refactoring complete.
- Behavior confirmed via `verify_rules_logic.py`:
  - Default initialization correctly falls back to `config.py`.
  - Injected dependency correctly overrides parameters.

## Configuration Flow
1. **User** edits parameters in Web UI.
2. **Web App** saves parameters to `data/config/trading_rules.json`.
3. **Analysis Tools** (`main.py`, visualizer, etc.) load `rules.json` on startup.
4. **Trading Logic** (`ImprovedTradingRules`) uses loaded parameters for analysis.
   - *Fallback*: If `rules.json` is missing, defaults to static values in `python/config.py`.
