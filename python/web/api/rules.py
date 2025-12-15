# python/web/api/rules.py
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from python.utils.diff_dict import calculate_diff
from python.web.schemas import TradingRules

# Setup Logger
DATA_DIR = Path("data/rules")
LOG_DIR = DATA_DIR
LOG_FILE = LOG_DIR / "rules.log"

# Ensure log directory exists
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("trading_rules")
logger.setLevel(logging.INFO)

# File Handler
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
logger.addHandler(file_handler)

# Stream Handler (Console)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
logger.addHandler(stream_handler)


DRAFT_PATH = DATA_DIR / "trading_rules.draft.json"
ACTIVE_PATH = DATA_DIR / "trading_rules.active.json"
HISTORY_DIR = DATA_DIR / "history"
INDEX_PATH = HISTORY_DIR / "index.json"

router = APIRouter()

# ... existing imports ...


def save_history(
    old_rules: Optional[Dict[str, Any]], new_rules: Dict[str, Any], meta
) -> None:
    """ルールの変更履歴を保存する"""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    diff = calculate_diff(old_rules, new_rules) if old_rules else {}

    record = {
        "meta": {
            "version": meta.version,
            "applied_at": meta.updated_at.isoformat(),
            "applied_by": meta.updated_by,
            "comment": meta.comment,
        },
        "rules": new_rules,
        "diff": diff,
    }

    filename = f"{meta.updated_at.strftime('%Y-%m-%dT%H-%M-%S')}_v{meta.version}.json"
    with open(HISTORY_DIR / filename, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    index = []
    if INDEX_PATH.exists():
        with open(INDEX_PATH, encoding="utf-8") as f:
            try:
                index = json.load(f)
            except json.JSONDecodeError:
                index = []

    # メタデータをインデックスに追加
    index_entry = {
        "version": meta.version,
        "applied_at": meta.updated_at.isoformat(),
        "applied_by": meta.updated_by,
        "comment": meta.comment,
    }
    index.append(index_entry)

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def is_market_open() -> bool:
    """
    現在が市場開場時間 (平日 09:00 - 15:00 JST) かどうかを判定する。
    """
    # JST = UTC+9
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)

    # 曜日チェック (0=Monday, 6=Sunday)
    if now.weekday() >= 5:  # 土日は休み
        return False

    # 時間チェック (9:00 - 15:00)
    current_time = now.time()
    market_open = datetime.strptime("09:00", "%H:%M").time()
    market_close = datetime.strptime("15:00", "%H:%M").time()

    return market_open <= current_time <= market_close


def evaluate_rule_risk(rules: TradingRules) -> List[str]:
    """
    ルールのリスク評価を行い、警告メッセージのリストを返す
    """
    risks = []
    rm = rules.risk_management

    # Market Hours Warning
    if is_market_open():
        risks.append(
            "Market is currently OPEN (09:00-15:00 JST). Changing rules now may disrupt the bot."
        )

    # 1. Stop Loss Check
    if rm.stop_loss_percent > 0.10:  # 10%
        risks.append(
            f"Stop loss ({rm.stop_loss_percent:.1%}) is extremely loose (>10%)."
        )

    # 2. Take Profit Check
    if rm.take_profit_percent > 0.50:  # 50%
        risks.append(
            f"Take profit ({rm.take_profit_percent:.1%}) is unusually high (>50%)."
        )

    # 3. Risk Per Trade
    if rm.risk_per_trade > 0.05:  # 5%
        risks.append(
            f"Risk per trade ({rm.risk_per_trade:.1%}) is very high (>5%). Standard is 1-2%."
        )

    # 4. Max Daily Loss
    if rm.max_daily_loss_percent > 0.20:  # 20%
        risks.append(
            f"Max daily loss ({rm.max_daily_loss_percent:.1%}) allows significant drawdown (>20%)."
        )

    # 5. Volatility Threshold (Market Filters)
    if rules.filters.volatility_threshold > 0.05:  # 5%
        risks.append(
            f"Volatility threshold ({rules.filters.volatility_threshold:.1%}) might ignore high volatility conditions."
        )

    return risks


@router.post("/")
def save_draft_rules(rules: TradingRules):
    DRAFT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DRAFT_PATH, "w", encoding="utf-8") as f:
        json.dump(rules.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
    return rules


@router.get("/active", response_model=TradingRules)
def get_active_rules_endpoint():
    """
    現在のアクティブなルールを取得する。
    ファイルが存在しない場合はデフォルト値を返す。
    """
    from python.utils.rules_loader import get_active_rules

    return get_active_rules()


@router.post("/apply")
def apply_rules(force: bool = False):
    if not DRAFT_PATH.exists():
        raise HTTPException(status_code=400, detail="Draft rules not found")

    # 1. draft 読み込み
    with open(DRAFT_PATH, encoding="utf-8") as f:
        raw = json.load(f)

    # 2. スキーマ検証
    try:
        rules = TradingRules.model_validate(raw)
    except Exception as e:
        logger.error(f"Rule validation failed: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid pricing rules: {str(e)}")

    if not rules.is_active:
        raise HTTPException(status_code=400, detail="Rules are inactive")

    # 3. リスク評価
    risk_flags = evaluate_rule_risk(rules)

    # 4. 危険ルールなら UI に確認させる
    if risk_flags and not force:
        logger.info(f"Rule application paused for confirmation. Risks: {risk_flags}")
        return {
            "status": "NEED_CONFIRM",
            "risk_flags": risk_flags,
        }

    # 5. Activeルール読込（バージョン管理用）
    old_raw = None
    if ACTIVE_PATH.exists():
        with open(ACTIVE_PATH, encoding="utf-8") as f:
            old_raw = json.load(f)

    # バージョンインクリメント
    current_version = 0
    if old_raw and "meta" in old_raw and "version" in old_raw["meta"]:
        v_val = old_raw["meta"]["version"]
        current_version = int(v_val) if v_val else 0

    new_version = current_version + 1
    now = datetime.utcnow()

    # update meta
    raw["meta"]["version"] = new_version
    raw["meta"]["updated_at"] = now.isoformat()
    if "updated_by" not in raw["meta"]:
        raw["meta"]["updated_by"] = "system"

    updated_rules = TradingRules.model_validate(raw)

    # 6. 履歴保存
    save_history(old_raw, raw, updated_rules.meta)

    # 7. Active保存 (Atomic Write)
    ACTIVE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # .tmp ファイルに書き込んでから rename することでアトミック更新を保証
    tmp_path = ACTIVE_PATH.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2, ensure_ascii=False)

    tmp_path.replace(ACTIVE_PATH)

    # LOGGING SUCCESS
    msg = f"Rules updated to version v{new_version} by {updated_rules.meta.updated_by}."
    if force and risk_flags:
        msg += f" [FORCE APPLIED with Risks: {risk_flags}]"

    logger.info(msg)

    return {
        "status": "APPLIED",
        "version": updated_rules.meta.version,
        "applied_at": now,
    }


@router.get("/history")
def list_history():
    if not INDEX_PATH.exists():
        return []
    try:
        return json.load(open(INDEX_PATH))
    except json.JSONDecodeError:
        return []


@router.get("/history/{version}")
def get_history(version: int):
    # バージョン番号が含まれるファイルを探す
    # ファイル名形式: YYYY-MM-DDTHH-MM-SS_v{version}.json
    if not HISTORY_DIR.exists():
        raise HTTPException(404, "History directory not found")

    for f in HISTORY_DIR.glob(f"*_v{version}.json"):
        with open(f, encoding="utf-8") as file:
            return json.load(file)

    raise HTTPException(404, f"History version {version} not found")
