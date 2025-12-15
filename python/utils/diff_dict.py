from typing import Dict, Any, List


def diff_dict(old: Dict[str, Any], new: Dict[str, Any], prefix: str = "") -> List[Dict[str, Any]]:
    diffs = []

    for key in new:
        full_key = f"{prefix}.{key}" if prefix else key

        if key not in old:
            diffs.append({"field": full_key, "before": None, "after": new[key], "type": "added"})
            continue

        if isinstance(new[key], dict) and isinstance(old[key], dict):
            diffs.extend(diff_dict(old[key], new[key], full_key))
        else:
            if new[key] != old[key]:
                diffs.append({"field": full_key, "before": old[key], "after": new[key], "type": "changed"})

    return diffs


def flatten(d: dict, parent_key="", sep="."):
    items = {}
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.update(flatten(v, new_key, sep))
        else:
            items[new_key] = v
    return items


def calculate_diff(before: dict, after: dict) -> dict:
    diff = {}
    flat_before = flatten(before)
    flat_after = flatten(after)

    for key in flat_after:
        if flat_before.get(key) != flat_after.get(key):
            diff[key] = {
                "before": flat_before.get(key),
                "after": flat_after.get(key),
            }
    return diff
