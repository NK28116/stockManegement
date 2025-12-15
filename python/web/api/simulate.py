# python/web/api/simulate.py
import json
from pathlib import Path

from fastapi import APIRouter

from python.web.schemas import TradingRules
from python.web.services.backtest import run_backtest

router = APIRouter()
DRAFT_PATH = Path("data/rules/trading_rules.draft.json")


@router.post("/simulate")
def simulate_rules():
    if not DRAFT_PATH.exists():
        return {"error": "Draft rules not found"}

    raw = json.loads(DRAFT_PATH.read_text(encoding="utf-8"))
    rules = TradingRules.model_validate(raw)

    result = run_backtest(rules)

    return result
