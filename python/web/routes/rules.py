from fastapi import APIRouter, Depends, HTTPException

from python.web.schemas import TradingRules, TradingRulesUpdate
from python.web.services.rule_store import RuleStore, get_rule_store

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("/", response_model=TradingRules)
async def get_rules(store: RuleStore = Depends(get_rule_store)):
    try:
        return store.get_rules()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Rules config file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=TradingRules)
async def update_rules(
    updates: TradingRulesUpdate, store: RuleStore = Depends(get_rule_store)
):
    try:
        return store.update_rules(updates.model_dump(exclude_unset=True))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
