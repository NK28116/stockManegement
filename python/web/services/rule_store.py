import json
from pathlib import Path
from typing import Any, Dict

from python.web.schemas import TradingRules


class RuleStore:
    def __init__(self, config_path: Path):
        self.config_path = config_path

    def get_rules(self) -> TradingRules:
        if not self.config_path.exists():
            # Fallback or error - for now raise error as we created the file
            raise FileNotFoundError(f"Config file not found at {self.config_path}")

        with open(self.config_path, "r") as f:
            data = json.load(f)

        return TradingRules(**data)

    def update_rules(self, updates: Dict[str, Any]) -> TradingRules:
        current_rules = self.get_rules()
        current_data = current_rules.model_dump()

        # Apply updates
        for key, value in updates.items():
            if value is not None:
                current_data[key] = value

        new_rules = TradingRules(**current_data)

        # Write back to file
        with open(self.config_path, "w") as f:
            json.dump(new_rules.model_dump(), f, indent=2)

        return new_rules


# Dependency injection helper (can be moved if context grows)
def get_rule_store():
    # Ideally path comes from a central config or env
    root_dir = Path(__file__).resolve().parent.parent.parent.parent
    config_path = root_dir / "data" / "config" / "trading_rules.json"
    return RuleStore(config_path)
